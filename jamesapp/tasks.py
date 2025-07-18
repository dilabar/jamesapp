from datetime import time
from venv import logger
from agent.models import PhoneCall, ServiceDetail
from celery import shared_task, current_task
from django.utils import timezone
from jamesapp.redis_queue import dequeue_campaign_task
from jamesapp.utils import deduplicate_contacts, parse_csv
from twilio.rest import Client
from contact.models import BulkAction, Campaign, Contact, CustomField, Email, List, PhoneNumber, RevokedTask
from celery import current_app
from django.db import transaction
from celery import group
import time
from django.db.models import Prefetch, Count, Q
from celery.exceptions import MaxRetriesExceededError
from twilio.base.exceptions import TwilioRestException

MAX_CONCURRENT_CALLS = 10  # Adjust based on your Twilio capacity
CALL_RATE_LIMIT = 1  # 1000ms between call initiations
BATCH_SIZE = 500  # Optimal for most databases

@shared_task
def poll_and_process_queued_campaigns():
    for _ in range(10):  # Process max 10 tasks per run
        task_data = dequeue_campaign_task()
        if not task_data:
            break

        try:
            
            process_campaign_calls.delay(
                task_data['campaign_id'],
                task_data['user_id'],
                task_data['agent_id']
            )
            logger.info(f"Queued campaign {task_data['campaign_id']} for processing.")
        except Exception as e:
            logger.error(f"Failed to dispatch campaign task: {str(e)}")

@shared_task(bind=True)
def process_campaign_calls(self, campaign_id, user_id, agent_id):
    logger.info(f'[Main Task] Celery started: {self.request.id}')

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found.")
        return f"Campaign {campaign_id} not found."

    campaign.status = 'started'
    campaign.triggers['task_id'] = self.request.id
    campaign.save()

    recipients = campaign.get_recipients()
    agents = list(campaign.agents.all().order_by('id'))
    if not agents:
        logger.error(f"No agents assigned to campaign {campaign.id}")
        return "No agents assigned."
    num_agents = len(agents)
    agent_index = 0
    for contact in recipients.iterator(chunk_size=500):
        try:
            primary_phone = contact.phone_numbers.first()
            if not primary_phone:
                continue

            phone_number = f"{primary_phone.country_code or ''}{primary_phone.phone_number}".strip()
            agent = agents[agent_index % num_agents]  # Round-robin logic

            phone_call = PhoneCall.objects.create(
                phone_number=phone_number,
                call_status='pending',
                user_id=user_id,
                agent_id=agent.id,
                campaign=campaign,
                contact=contact
            )

            # Call the sub-task asynchronously
            initiate_call.delay(phone_call.id, user_id, agent.id, campaign_id)
            agent_index += 1

        except Exception as e:
            logger.error(f"Failed to queue contact {contact.id}: {str(e)}")
            continue

    campaign.triggers['queued_at'] = timezone.now().isoformat()
    campaign.status = 'sent'

    campaign.save()
    logger.info(f"[Main Task] Campaign {campaign.id} calls have been queued.")
    return f"[Main Task] Campaign {campaign.name} ({campaign.id}) calls have been queued."

@shared_task(bind=True, max_retries=3, default_retry_delay=60)  # Retry up to 3 times, 60s delay
def initiate_call(self, phone_call_id, user_id, agent_id, campaign_id):
    logger.info(f"[Sub-task] Initiating call for PhoneCall ID: {phone_call_id}")

    phone_call = None  # Ensure it's defined even if exception occurs before assignment

    try:
        CALL_BASE_URL = 'https://secretvoiceagent.net'
        phone_call = PhoneCall.objects.select_related('campaign').get(id=phone_call_id)
        campaign = phone_call.campaign

        twilio = ServiceDetail.objects.filter(user_id=user_id, service_name='twilio').first()
        if not twilio:
            logger.error("Twilio credentials not found.")
            phone_call.call_status = 'failed'
            phone_call.save()
            return "Twilio credentials not found."

        client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)

        call = client.calls.create(
            url=f'{CALL_BASE_URL}/call/start_twilio_stream/{user_id}/{agent_id}/{campaign_id}/',
            to=phone_call.phone_number,
            from_=campaign.twilio_phone.phone_number,
            record=True,
            method='POST',
            status_callback=f'{CALL_BASE_URL}/call/call_status_callback/{phone_call.id}/',
            status_callback_method='POST',
            status_callback_event=["initiated", "ringing", "answered", "completed"]
        )

        phone_call.call_status = 'initiated'
        phone_call.twilio_call_id = call.sid
        phone_call.save()
        return f"Call initiated successfully. Call SID: {call.sid}"

    except TwilioRestException as e:
        if e.status == 429 or "Too Many Requests" in str(e):  # Handle Twilio rate limiting
            logger.warning(f"Rate limit hit for PhoneCall {phone_call_id}, retrying...")
            try:
                raise self.retry(exc=e)
            except MaxRetriesExceededError:
                logger.error(f"Max retries exceeded for PhoneCall {phone_call_id}")
                if phone_call:
                    phone_call.call_status = 'failed'
                    phone_call.save()
                return "Max retries exceeded due to rate limit."

        logger.error(f"[Sub-task] Twilio error for {phone_call_id}: {str(e)}")
        if phone_call:
            phone_call.call_status = 'failed'
            phone_call.save()
        return f"Twilio error: {str(e)}"

    except Exception as e:
        logger.error(f"[Sub-task] Call failed for {phone_call_id}: {str(e)}")
        if phone_call:
            phone_call.call_status = 'failed'
            phone_call.save()
        return f"[Sub-task] Call failed for {phone_call_id}: {str(e)}"

# @shared_task(bind=True)
# def process_campaign_calls(self, campaign_id, user_id, agent_id):
#     logger.info(f'Celery task started: {self.request.id}')
    
#     try:
#         campaign = Campaign.objects.get(id=campaign_id)
#     except Campaign.DoesNotExist:
#         logger.error(f"Campaign {campaign_id} not found.")
#         return "Campaign not found."

#     twilio = ServiceDetail.objects.filter(user_id=user_id, service_name='twilio').first()
#     if not twilio:
#         campaign.status = 'failed'
#         campaign.triggers['error'] = 'Twilio service details not found.'
#         campaign.save()
#         return "Twilio service details not found."

#     client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)


#     if campaign.status in ["draft", "scheduled"]:
#      # Optimized recipient processing with prefetch

#         # # Optimized queryset with prefetching
#         recipients = campaign.get_recipients()

#         # Batch processing of phone calls
#         phone_calls_batch = []
#         for contact in recipients.iterator(chunk_size=1000):  # Memory-efficient iteration
#             try:
#                 primary_phone = contact.phone_numbers.first()
#                 if not primary_phone:
#                     continue

#                 phone_calls_batch.append(PhoneCall(
#                     phone_number=f"{primary_phone.country_code or ''}{primary_phone.phone_number}".strip(),
#                     call_status='pending',
#                     user_id=user_id,
#                     agent_id=campaign.agent.id,
#                     campaign=campaign,
#                     contact=contact
#                 ))

#                 # Batch insertion
#                 if len(phone_calls_batch) >= BATCH_SIZE:
#                     with transaction.atomic():
#                         PhoneCall.objects.bulk_create(
#                             phone_calls_batch,
#                             batch_size=BATCH_SIZE,
#                             ignore_conflicts=True
#                         )
#                     phone_calls_batch = []

#             except Exception as e:
#                 logger.error(f"Error processing contact {contact.id}: {str(e)}")
#                 continue

#         # Final batch insertion
#         if phone_calls_batch:
#             with transaction.atomic():
#                 PhoneCall.objects.bulk_create(
#                     phone_calls_batch,
#                     batch_size=BATCH_SIZE,
#                     ignore_conflicts=True
#                 )

#         # Update campaign status
#         campaign.status = 'started'
#         campaign.triggers['task_id'] = self.request.id
#         campaign.save(update_fields=['status', 'triggers'])

#     total_calls = 0
#     success = 0
#     failures = 0

#     CALL_BASE_URL = 'https://secretvoiceagent.net'

#     while PhoneCall.objects.filter(campaign=campaign, call_status='pending').exists():
#         # pending_count = PhoneCall.objects.filter(campaign=campaign, call_status='pending').count()
#         logger.info(f"counter total_calls {total_calls} success: {success}, failure {failures}")

#         if RevokedTask.objects.filter(task_id=self.request.id).exists():
#             campaign.status = 'paused'
#             campaign.save()
#             return True #"Campaign task paused."

#         # Get active calls count
#         active_calls = PhoneCall.objects.filter(
#             campaign=campaign,
#             call_status__in=['initiated', 'in-progress']
#         ).count()
#         logger.info(f"active_calls {active_calls} MAX_CONCURRENT_CALLS: {MAX_CONCURRENT_CALLS}")
        
#         # Calculate available slots
#         available_slots = MAX_CONCURRENT_CALLS - active_calls
#         if available_slots <= 0:
#             time.sleep(1)
#             continue


#         # Get pending calls with locking
#         pending_calls = PhoneCall.objects.select_for_update(
#             skip_locked=True
#         ).filter(
#             campaign=campaign,
#             call_status='pending'
#         )[:available_slots]
#         # Process the batch
#         success, failures = 0, 0
#         for phone_call in pending_calls:

#             try:
#                 logger.info(f"phone_call initate")

#                 call = client.calls.create(
#                     url=f'{CALL_BASE_URL}/call/start_twilio_stream/{user_id}/{agent_id}/{campaign_id}/',
#                     to=phone_call.phone_number,
#                     from_=campaign.twilio_phone.phone_number,
#                     record=True,
#                     method='POST',
#                     status_callback=f'{CALL_BASE_URL}/call/call_status_callback/{phone_call.id}/',
#                     status_callback_method='POST',
#                     status_callback_event=["initiated", "ringing", "answered", "completed"]
#                 )

#                 phone_call.call_status = 'initiated'
#                 phone_call.twilio_call_id = call.sid
#                 phone_call.save()
#                 success += 1
#                 time.sleep(CALL_RATE_LIMIT)

#             except Exception as e:
#                 logger.error(f"Call failed: {str(e)}")
#                 phone_call.call_status = 'failed'
#                 phone_call.save()
#                 failures += 1

#         logger.info(f"Processed: {success} success, {failures} failures")

#     # Final status update after loop completes
#     # failed_calls = PhoneCall.objects.filter(
#     #     campaign=campaign,
#     #     call_status='failed'
#     # ).count()
#     campaign.status = 'sent'
#     campaign.triggers['sent_at'] = timezone.now().isoformat()
#     campaign.save()

#     logger.info(f"Campaign {campaign.id} finalized with status: {campaign.status}")
#     return True #"Campaign calls processed successfully."


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
    

@shared_task
def run_campaign(campaign_id):
    # Campaign logic here
    # For example, update the status of the campaign, process data, etc.
    print(f"Running campaign {campaign_id}")
    return f"Campaign {campaign_id} is running"