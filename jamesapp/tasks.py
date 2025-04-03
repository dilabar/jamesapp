from datetime import time
from agent.models import PhoneCall, ServiceDetail
from celery import shared_task, current_task
from django.utils import timezone
from jamesapp.utils import deduplicate_contacts, parse_csv
from twilio.rest import Client
from contact.models import BulkAction, Campaign, Contact, CustomField, Email, List, PhoneNumber, RevokedTask
from celery import current_app

from celery import group
import time

MAX_CONCURRENT_CALLS = 2
CALL_RATE_LIMIT = 1  # 1 call per second


# @shared_task(bind=True)
# def process_campaign_calls(self, campaign_id, user_id, agent_id):
#     """
#     Processes campaign calls asynchronously with pause and resume support.
#     """
#     campaign = Campaign.objects.get(id=campaign_id)
#     twilio = ServiceDetail.objects.filter(user_id=user_id, service_name='twilio').first()

#     phone_calls = []
#     recipients = campaign.get_recipients()
#     if campaign.status in ["draft", "scheduled"]:
#         for contact in recipients:
#             phone_number = contact.phone_numbers.filter(is_primary=True).first()
#             if not phone_number:
#                 continue

#             # Format the phone number
#             country_code = phone_number.country_code or ''
#             phone_number_str = f"{country_code}{phone_number.phone_number}".strip()

#             # Create PhoneCall object
#             phone_call = PhoneCall(
#                 phone_number=phone_number_str,
#                 call_status='pending',
#                 user_id=user_id,
#                 agent_id=campaign.agent.id,
#                 campaign=campaign,
#                 contact=contact
#             )
#             phone_calls.append(phone_call)

#             # Bulk create phone call records
#         PhoneCall.objects.bulk_create(phone_calls)

#     if not twilio:
#         campaign.status = 'failed'
#         campaign.triggers['error']='Twilio service details not found.'
#         campaign.save()
#         return "Twilio service details not found."

#     client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)

#     # Store Task ID to Pause/Resume
#     campaign.status = 'started'

#     campaign.triggers['task_id'] = self.request.id  # Store Celery task ID in the campaign
#     campaign.save()
#     # CALL_RATE_LIMIT = 1 

#     # Loop through PhoneCalls to initiate
#     for phone_call in PhoneCall.objects.filter(campaign=campaign, call_status='pending'):
#         # Check if task is revoked (Paused)
#         if RevokedTask.objects.filter(task_id=self.request.id).exists():
#             # If the task is revoked, stop the execution.
#             campaign.status = 'paushed'
#             campaign.save()
#             return "Campaign task paused."

#         try:
#             call = client.calls.create(
#                 url=f'https://ee76-2409-40e1-303c-fb20-7149-2cec-c56a-64.ngrok-free.app/call/start_twilio_stream/{user_id}/{agent_id}/{campaign_id}/',
#                 to=phone_call.phone_number,
#                 from_=twilio.decrypted_twilio_phone,
#                 record=True,
#                 method='POST',
#                 status_callback=f'https://ee76-2409-40e1-303c-fb20-7149-2cec-c56a-64.ngrok-free.app/call/call_status_callback/{phone_call.id}/',
#                 status_callback_method='POST',
#                 status_callback_event=["initiated", "ringing", "answered", "completed"]
#             )

#             phone_call.call_status = 'initiated'
#             phone_call.twilio_call_id = call.sid
#             phone_call.save()
#             # Introduce a delay to avoid Twilio rate limits
#             # time.sleep(1 / CALL_RATE_LIMIT)

#         except Exception as e:
#             phone_call.call_status = 'failed'
            
#             phone_call.save()
#             # Log or handle exception here (e.g., log the error or message)
#             print(f"Error initiating call for {phone_call.phone_number}: {str(e)}")

#     # After processing all calls, mark the campaign as 'sent'
#     campaign.status = 'sent'
#     campaign.triggers['sent_at'] = timezone.now().isoformat()
#     campaign.save()
#     return "Campaign calls processed successfully."
@shared_task(bind=True)
def process_campaign_calls(self, campaign_id, user_id, agent_id):
    """
    Processes campaign calls asynchronously with batch-wise execution (5 calls at a time).
    """
    campaign = Campaign.objects.get(id=campaign_id)
    twilio = ServiceDetail.objects.filter(user_id=user_id, service_name='twilio').first()

    if not twilio:
        campaign.status = 'failed'
        campaign.triggers['error'] = 'Twilio service details not found.'
        campaign.save()
        return "Twilio service details not found."

    client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)

    # Pehle bulk me saari phone calls create karein
    if campaign.status in ["draft", "scheduled"]:
        phone_calls = []
        recipients = campaign.get_recipients()

        for contact in recipients:
            phone_number = contact.phone_numbers.filter(is_primary=True).first()
            if not phone_number:
                continue

            phone_number_str = f"{phone_number.country_code or ''}{phone_number.phone_number}".strip()

            phone_call = PhoneCall(
                phone_number=phone_number_str,
                call_status='pending',
                user_id=user_id,
                agent_id=campaign.agent.id,
                campaign=campaign,
                contact=contact
            )
            phone_calls.append(phone_call)

        PhoneCall.objects.bulk_create(phone_calls)
        campaign.status = 'started'
        campaign.triggers['task_id'] = self.request.id
        campaign.save()

    # Process calls in batches, ensuring max 5 active calls at a time
    while PhoneCall.objects.filter(campaign=campaign, call_status='pending').exists():
        # Check if campaign is paused
        if RevokedTask.objects.filter(task_id=self.request.id).exists():
            campaign.status = 'paused'
            campaign.save()
            return "Campaign task paused."

        # Get the number of active calls
        active_calls = PhoneCall.objects.filter(campaign=campaign, call_status__in=['initiated', 'in-progress']).count()

        if active_calls >= MAX_CONCURRENT_CALLS:
            time.sleep(2)  # Wait and check again
            continue

        # Get the next pending call (only if active calls < 5)
        pending_calls = PhoneCall.objects.filter(campaign=campaign, call_status='pending')[:(MAX_CONCURRENT_CALLS - active_calls)]

        for phone_call in pending_calls:
            try:
                call = client.calls.create(
                    url=f'https://secretvoiceagent.net/call/start_twilio_stream/{user_id}/{agent_id}/{campaign_id}/',
                    to=phone_call.phone_number,
                    from_=twilio.decrypted_twilio_phone,
                    record=True,
                    method='POST',
                    status_callback=f'https://secretvoiceagent.net/call/call_status_callback/{phone_call.id}/',
                    status_callback_method='POST',
                    status_callback_event=["initiated", "ringing", "answered", "completed"]
                )

                phone_call.call_status = 'initiated'
                phone_call.twilio_call_id = call.sid
                phone_call.save()

                time.sleep(CALL_RATE_LIMIT)  # Maintain rate limit

            except Exception as e:
                phone_call.call_status = 'failed'
                phone_call.save()
                print(f"Error initiating call for {phone_call.phone_number}: {str(e)}")

    # Mark campaign as completed
    campaign.status = 'sent'
    campaign.triggers['sent_at'] = timezone.now().isoformat()
    campaign.save()
    return "Campaign calls processed successfully."
def pause_task(task_id):
    """Revoke a Celery task and store it in the database."""
    current_app.control.revoke(task_id, terminate=True)  # Revoke the task
    RevokedTask.objects.create(task_id=task_id)  # Store the revoked task ID in DB
    print(f"Task {task_id} revoked and stored in DB.")


def resume_task(campaign_id, user_id, agent_id):
    """Resume the campaign task by re-triggering the Celery task."""
    # Re-push the task to Celery to resume execution
    process_campaign_calls.apply_async(args=[campaign_id, user_id, agent_id])
    print(f"Campaign {campaign_id} task resumed.")


@shared_task
def process_bulk_action(action_id):
    """
    Celery task to process the bulk action.
    """
    action = BulkAction.objects.get(id=action_id)
    action.status = "PROCESSING"
    action.started_at = timezone.now()
    action.save()

    try:
        file_path = action.csv_file.path
        contacts_data = parse_csv(file_path)

        deduplication = action.data.get("deduplication", "email,phone")
        listId = action.data.get("listId", "")
        import_option = action.data.get("importOption", "create")
        field_mappings = action.data.get("field_mappings", [])

        predefined_fields = {str(field.id): field for field in CustomField.objects.filter(is_predefined=True)}
        custom_fields = {str(field.id): field for field in CustomField.objects.filter(user=action.user, is_predefined=False)}
        all_fields = {**predefined_fields, **custom_fields}

        for row in contacts_data:
            if action.status == 'PAUSED':
                continue  # Skip processing if paused
            if action.status == 'FAILED':
                break  # Stop processing if failed

            try:
                contact_data = {}
                dynamic_field_data = {}

                for field_mapping in field_mappings:
                    field_id = str(field_mapping['field_id'])
                    csv_header = field_mapping['csv_header']
                    mapped_field = all_fields.get(field_id)

                    if mapped_field:
                        if mapped_field.is_predefined:
                            contact_data[mapped_field.unique_key] = row.get(csv_header, "").strip()
                        else:
                            dynamic_field_data[mapped_field.unique_key] = row.get(csv_header, "").strip()

                first_name = contact_data.get("first_name", "")
                last_name = contact_data.get("last_name", "")
                email = contact_data.get("email", "")
                phone_number = contact_data.get("phone_number", "")
                contact_type = contact_data.get("contact_type", "")

                existing_contacts = deduplicate_contacts({"email": email, "phone": phone_number}, deduplication)
                if existing_contacts.exists():
                    if import_option in ("update", "create_update"):
                        contact = existing_contacts.first()
                        contact.first_name = first_name
                        contact.last_name = last_name
                        contact.contact_type = contact_type
                        contact.custom_fields.update(dynamic_field_data)
                        contact.save()
                else:
                    contact = Contact.objects.create(
                        user=action.user,
                        first_name=first_name,
                        last_name=last_name,
                        contact_type=contact_type,
                        custom_fields=dynamic_field_data,
                    )

                    if email:
                        Email.objects.create(contact=contact, email=email, user=action.user, is_primary=True)
                    if phone_number:
                        PhoneNumber.objects.create(contact=contact, phone_number=phone_number, user=action.user, is_primary=True)

                list_obj = List.objects.get(id=listId)
                list_obj.contacts.add(contact)

                action.success_count += 1
            except Exception as e:
                action.failure_count += 1
                action.error_details.append({
                    'row': row,
                    'error': str(e)
                })

            action.save()

        action.status = "COMPLETED"
        action.completed_at = timezone.now()
        action.save()

    except Exception as e:
        action.status = "FAILED"
        action.error_message = str(e)
        action.completed_at = timezone.now()
        action.save()
        raise e