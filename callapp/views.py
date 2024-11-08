from base64 import urlsafe_b64encode
import pandas as pd
from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from agent.models import PhoneCall, ServiceDetail
from jamesapp.utils import fetch_data_from_api
from twilio.rest import Client
import json
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse, Start, Stream,Connect
from django.conf import settings

from django.contrib import messages
import logging
logger = logging.getLogger(__name__)


# Twilio API credentials

@login_required
def call_initiate(request, agent_id):
    twilio = ServiceDetail.objects.filter(user=request.user, service_name='twilio').first()
    client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)
    # Handle form submission
    if request.method == "POST":
        phone_number = request.POST.get('phone_number')
        file_upload = request.FILES.get('file_upload')
        
        # Manual entry handling
        if phone_number:
            # Save phone call log for manual entry
            phone_call = PhoneCall.objects.create(
                phone_number=phone_number,
                call_status='pending'
            )
            # Place the call
            try:
                call = client.calls.create(
                    url=f'{request.scheme}://{request.get_host()}/call/start_twilio_stream/{request.user.id}/{agent_id}/',
                    to=phone_call.phone_number,
                    from_=twilio.decrypted_twilio_phone
                )
                phone_call.call_status = 'initiated'
                phone_call.twilio_call_id = call.sid
                phone_call.save()
            except Exception as e:
                return HttpResponse(f"Error initiating call to {phone_call.phone_number}: {str(e)}")

        # CSV/Excel upload handling
        elif file_upload:
            # Save file temporarily
            file_path = default_storage.save(file_upload.name, file_upload)
            ext = file_upload.name.split('.')[-1].lower()
            try:
                # Read file based on extension
                if ext == 'csv':
                    data = pd.read_csv(default_storage.open(file_path))
                elif ext in ['xls', 'xlsx']:
                    data = pd.read_excel(default_storage.open(file_path))
                else:
                    return HttpResponse("Unsupported file format. Please upload a CSV or Excel file.")

                # Extract phone numbers and initiate calls
                for _, row in data.iterrows():
                    phone = row.get('phone_number')
                    if phone:
                        phone_call = PhoneCall.objects.create(
                            phone_number=phone,
                            call_status='pending'
                        )
                        try:
                            call = client.calls.create(
                                url=f'{request.scheme}://{request.get_host()}/call/start_twilio_stream/{request.user.id}/{agent_id}/',
                                to=phone_call.phone_number,
                                from_=twilio.twilio_phone
                            )
                            phone_call.call_status = 'initiated'
                            phone_call.twilio_call_id = call.sid
                            phone_call.save()
                        except Exception as e:
                            return messages.success(f"Error initiating call to {phone_call.phone_number}: {str(e)}")

            finally:
                default_storage.delete(file_path)  # Clean up the temporary file
        messages.success(request, 'Call Initiated successfully!')

        # return redirect('agent:agent_list')
        
    return render(request, 'callapp/initiate_call.html')


   
@csrf_exempt
def start_twilio_stream(request, user_id,agent_id):
    response = VoiceResponse()
    
    # Define your WebSocket URL to receive the Twilio stream data
    stream_url = f"wss://{request.get_host()}/ws/play_ai/{user_id}/{agent_id}/"

    try:
        connect = Connect()
        connect.stream(name='Twilio Stream', url=stream_url)
        response.append(connect)
     
        # # Optional: Play an initial message or beep
        # response.say('The stream has started. You may now begin speaking.')
        
    except Exception as e:
        logger.error(f"Error starting Twilio stream: {str(e)}")
        response.say("Error starting the audio stream. Please try again later.")
    
    return HttpResponse(str(response), content_type="text/xml")
@login_required
def getcall_log(request):
    twilio = ServiceDetail.objects.filter(user=request.user, service_name='twilio').first()
    client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)
    calls = client.calls.list(limit=20)

    for record in calls:
        print(record.sid)

    context={
        'calls_list':calls
    }
    return render(request, 'twilio_log/call_log.html',context)
@login_required
def get_twilio_call_recordings(request,call_sid):
    twilio = ServiceDetail.objects.filter(user=request.user, service_name='twilio').first()
    client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)

    try:
        # Fetch recordings for the specified call SID
        recordings = client.recordings.list(call_sid=call_sid)

        # Log each recording for debugging
        for recording in recordings:
            print(recording.sid, recording.date_created, recording.duration)

        # Pass recordings to the template
        context = {
            'recordings': recordings
        }

    except Exception as e:
        # Handle exceptions (e.g., Twilio errors)
        print(f"Error fetching recordings: {e}")
        context = {
            'recordings': [],
            'error': f"Could not retrieve recordings: {e}"
        }
    return render(request, 'twilio_log/recording.html',context)