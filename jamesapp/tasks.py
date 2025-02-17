from datetime import time
from agent.models import PhoneCall, ServiceDetail
from celery import shared_task, current_task
from django.utils import timezone
from twilio.rest import Client
from contact.models import Campaign, RevokedTask
from celery import current_app


@shared_task(bind=True)
def process_campaign_calls(self, campaign_id, user_id, agent_id):
    """
    Processes campaign calls asynchronously with pause and resume support.
    """
    campaign = Campaign.objects.get(id=campaign_id)
    twilio = ServiceDetail.objects.filter(user_id=user_id, service_name='twilio').first()

    phone_calls = []
    recipients = campaign.get_recipients()
    if campaign.status in ["draft", "scheduled"]:
        for contact in recipients:
            phone_number = contact.phone_numbers.filter(is_primary=True).first()
            if not phone_number:
                continue

            # Format the phone number
            country_code = phone_number.country_code or ''
            phone_number_str = f"{country_code}{phone_number.phone_number}".strip()

            # Create PhoneCall object
            phone_call = PhoneCall(
                phone_number=phone_number_str,
                call_status='pending',
                user_id=user_id,
                agent_id=campaign.agent.id,
                campaign=campaign,
                contact=contact
            )
            phone_calls.append(phone_call)

            # Bulk create phone call records
        PhoneCall.objects.bulk_create(phone_calls)

    if not twilio:
        campaign.status = 'failed'
        campaign.triggers['error']='Twilio service details not found.'
        campaign.save()
        return "Twilio service details not found."

    client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)

    # Store Task ID to Pause/Resume
    campaign.status = 'started'

    campaign.triggers['task_id'] = self.request.id  # Store Celery task ID in the campaign
    campaign.save()
    # CALL_RATE_LIMIT = 1 

    # Loop through PhoneCalls to initiate
    for phone_call in PhoneCall.objects.filter(campaign=campaign, call_status='pending'):
        # Check if task is revoked (Paused)
        if RevokedTask.objects.filter(task_id=self.request.id).exists():
            # If the task is revoked, stop the execution.
            campaign.status = 'paushed'
            campaign.save()
            return "Campaign task paused."

        try:
            call = client.calls.create(
                url=f'https://secretvoiceagent.net/call/start_twilio_stream/{user_id}/{agent_id}/',
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
            # Introduce a delay to avoid Twilio rate limits
            # time.sleep(1 / CALL_RATE_LIMIT)

        except Exception as e:
            phone_call.call_status = 'failed'
            
            phone_call.save()
            # Log or handle exception here (e.g., log the error or message)
            print(f"Error initiating call for {phone_call.phone_number}: {str(e)}")

    # After processing all calls, mark the campaign as 'sent'
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
