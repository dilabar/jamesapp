from datetime import time, timedelta
import random
from django.conf import settings
from django.http import HttpResponse
import requests
from twilio.rest import Client
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import urllib
from django.core.paginator import Paginator
from django.db.models import F

from jamesapp.utils import decrypt, get_transcript_data
from .models import PhoneCall, ServiceDetail,GoogleCalendarEvent
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

@login_required
def call_history(request):
    # Fetch phone calls for the logged-in user
    phone_calls = (
        PhoneCall.objects.filter(user=request.user)
        .order_by(F('timestamp').desc(nulls_last=True))  # Order by 'date' descending
    )

    # Apply offset and limit for pagination
    page_number = request.GET.get('page', 1)  # Default to the first page
    limit = 10  # Number of records per page
    offset = (int(page_number) - 1) * limit  # Calculate offset
    paginated_calls = phone_calls[offset:offset + limit]
    # Calculate the total number of pages
    total_records = phone_calls.count()
    total_pages = (total_records + limit - 1) // limit  # Ceil division

    context = {
        'page_obj': paginated_calls,  # Paginated phone calls
        'page_number': page_number,  # Current page number
        'total_pages': total_pages,  # Total number of pages
        'page_range': range(1, total_pages + 1),  # Create a range of pages
    }
    return render(request, 'new/call_history.html', context)
@login_required
def call_detail(request, id):
    obj = PhoneCall.objects.filter(user=request.user, id=id).first()
    if not obj:
        return render(request, 'new/error.html', {'message': 'Call not found'})  # Handle missing call object

    play_ai = ServiceDetail.objects.filter(user=request.user, service_name='play_ai').first()
    ag=decrypt(obj.agent_id)
    transcript = None
    data = get_transcript_data(ag,obj.play_ai_conv_id,play_ai.decrypted_api_key,play_ai.decrypted_account_sid,100,0)
    if data:
        transcript=data

    


    # Calculate end time
    if obj.timestamp and obj.call_duration:
        end_time = obj.timestamp + timedelta(seconds=obj.call_duration)
    else:
        end_time = None  # Handle invalid data
    print(transcript)
    # Prepare context
    context = {
        'call_obj': obj,
        'end_time': end_time,
        'transcript': transcript
    }
    return render(request, 'new/call_details.html', context)
@login_required
def agent_setup(request):
    
    return render(request, 'new/list.html')

@login_required
def fetch_twilio_recording(request,recording_url):
    recording_url = urllib.parse.unquote(recording_url)
    twilio = ServiceDetail.objects.filter(user=request.user, service_name='twilio').first()
    # Fetch the recording from Twilio
    response = requests.get(recording_url, auth=(twilio.decrypted_account_sid,twilio.decrypted_api_key))
    
    if response.status_code == 200:

        # Serve the recording as an audio file
        return HttpResponse(response.content, content_type="audio/mpeg")
    else:
        return HttpResponse("Recording not found or unauthorized.", status=404)

@login_required
def onboard(request):
    
    return render(request, 'new/agent_onboard.html')


@csrf_exempt
def playai_webhook(request):
    """
    Handles Play.ai webhook calls, creates a Google Calendar event, and saves details to the database.
    """
    if request.method == "POST":
        try:
            # Parse incoming JSON payload
            data = json.loads(request.body)
            print(data)
            # Extract event details from the payload
            summary = data.get("summary", "No Title")
            start_time = data.get("start_time")
            end_time = data.get("end_time")
            description = data.get("description", "No Description")
            attendees = data.get("attendees", [])

            # # Google Calendar API setup using service account
            # SCOPES = ['https://www.googleapis.com/auth/calendar']
            # credentials = service_account.Credentials.from_service_account_file(
            #     'client_secret.json', scopes=SCOPES
            # )
            # service = build('calendar', 'v3', credentials=credentials)

            # # Create Google Calendar event payload
            # event = {
            #     "summary": summary,
            #     "description": description,
            #     "start": {"dateTime": start_time, "timeZone": "UTC"},
            #     "end": {"dateTime": end_time, "timeZone": "UTC"},
            #     "attendees": [{"email": attendee} for attendee in attendees],
            # }

            # Call Google Calendar API to create event
            # calendar_event = service.events().insert(calendarId='primary', body=event).execute()

            # Save event details to the database
            saved_event = GoogleCalendarEvent.objects.create(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                attendees=attendees,
                calendar_event_id=f"event_{random.randint(1000, 9999)}",
           
                calendar_link=f"http://127.0.0.1:4040/?event_{random.randint(1000, 9999)}",
            )

            # Respond with success and event details
            return JsonResponse({
                "status": "success",
                "message": "Event booked successfully.",
                "event": {
                    "id": saved_event.id,
                    "summary": saved_event.summary,
                    "start_time": saved_event.start_time,
                    "end_time": saved_event.end_time,
                    "calendar_link": saved_event.calendar_link,
                },
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error occurred: {str(e)}"}, status=400)

    # Handle non-POST requests
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)