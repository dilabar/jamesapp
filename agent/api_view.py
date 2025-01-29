from datetime import datetime, time, timedelta
from hashlib import sha256
import hashlib
import os
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

from rateMaster.models import CallRate
from scheduling.models import CalendarConnection
from jamesapp.utils import decrypt, encrypt, get_transcript_data
from .models import Agent, PhoneCall, ServiceDetail,GoogleCalendarEvent
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

def calculate_bill(call):
    """
    Calculate the total bill for a phone call, including forwarded calls if applicable.
    """
    rates = CallRate.objects.filter(is_active=True)  # Fetch only active rates
    total_bill = 0

    # Helper function to calculate the bill for a single call
    def calculate_single_call(call):
        call_start = call.timestamp  # Use `timestamp` as the start time
        call_duration = call.call_duration or 0  # Default to 0 if missing
        call_end = call_start + timedelta(seconds=call_duration)  # Derive end time

        bill = 0
        for rate in rates:
            # Assuming rates are active 24/7 since no time intervals are defined
            overlap_seconds = call_duration
            bill += overlap_seconds * rate.price_per_second

        return round(bill, 2)

    # Calculate bill for the main call
    total_bill += calculate_single_call(call)

    # Include bills for forwarded calls (if any)
    forwarded_calls = PhoneCall.objects.filter(from_call_id=call)
    for forwarded_call in forwarded_calls:
        total_bill += calculate_single_call(forwarded_call)

    return total_bill

@login_required
def call_history(request):
    # Fetch phone calls for the logged-in user
    # print(f"start..........")
    # phone_cals = PhoneCall.objects.all()  # Filter by user if required

    # for phone_call in phone_cals:
    #     print(f"phone_call..........",phone_call.id)

    #     # Retrieve the Agent object based on agent_id
    #     if phone_call.agent_id:
    #         ag=decrypt(phone_call.agent_id)
    #         hs=hashlib.sha256(ag.encode()).hexdigest()
    #         print(f"ag..........",ag)
    #         print(f"hs..........",hs)
       
    #         agent = get_object_or_404(Agent, agent_id_hash=hs)  # Match by agent_id

    #         # Update the PhoneCall with the corresponding Agent
    #         phone_call.agnt = agent  # Set the agent foreign key field
    #         phone_call.save()  # Save the updated PhoneCall object
    #         print(f"phone_call..........",phone_call.id)
    #     # else:
    #     # phone_call.agent_id=encrypt("YOUR-AI-CLONE-0k26dDh7LesuHadHoV8YH")

    #     # print(f"phone_call. update.........",phone_call.id)
    #     # phone_call.save()

    # print(f"done..........")
        
    # phone_calls = (
    #     PhoneCall.objects.filter(user=request.user)
    #     .order_by(F('timestamp').desc(nulls_last=True))  # Order by 'date' descending
    # )
    # Determine whether the user is an agency or a sub-account
    if request.user.is_agency:
        # Get the agency's sub-accounts and include the agency itself
        user_queryset = request.user.get_all_subaccounts()
    else:
        # For sub-account users, only fetch their own calls
        user_queryset = [request.user]
    phone_calls = (
        PhoneCall.objects.filter(user__in=user_queryset)
        .select_related('agnt')  # Include related Agent data (join with Agent model)
        .order_by(F('timestamp').desc(nulls_last=True))  # Order by 'timestamp' descending
    )
    # Apply offset and limit for pagination
    page_number = request.GET.get('page', 1)  # Default to the first page
    limit = 10  # Number of records per page
    offset = (int(page_number) - 1) * limit  # Calculate offset
    paginated_calls = phone_calls[offset:offset + limit]

        # Add billing data for each call
    for call in paginated_calls:
        call.bill = calculate_bill(call)
    # Calculate the total number of pages
    total_records = phone_calls.count()
    total_pages = (total_records + limit - 1) // limit  # Ceil division
    # print(paginated_calls.first().agnt)
    context = {
        'page_obj': paginated_calls,  # Paginated phone calls
        'page_number': page_number,  # Current page number
        'total_pages': total_pages,  # Total number of pages
        'page_range': range(1, total_pages + 1),  # Create a range of pages
    }
    return render(request, 'new/calls_history.html', context)
@login_required
def call_detail(request, id):
    # obj = PhoneCall.objects.filter(user=request.user, id=id).first()
    obj = PhoneCall.objects.select_related('agnt').filter(user=request.user, id=id).first()
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
    # Prepare context
    context = {
        'call_obj': obj,
        'end_time': end_time,
        'transcript': transcript
    }
    return render(request, 'new/all_conversation_log.html', context)
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
            # Extract event details from the payload
            summary = data.get("summary", "No Title")
            start_time = data.get("start_time")
            end_time = data.get("end_time")
            description = data.get("description", "No Description")
            attendees = data.get("attendees")
            agentId = data.get("agentId")
            agent_id_hash = sha256(agentId.encode()).hexdigest()

            agd=Agent.objects.filter(agent_id_hash=agent_id_hash).first()

            # Optionally, add to Google Calendar
            user = agd.user  # Ensure the user is set correctly
            calendar_connection = CalendarConnection.objects.get(user_id=user)
            if calendar_connection.provider == 'google':
                raw_credentials = calendar_connection.credentials
                credentials = Credentials(
                token=raw_credentials.get("token"),
                refresh_token=raw_credentials.get("refresh_token"),
                token_uri=raw_credentials.get("token_uri"),
                client_id=raw_credentials.get("client_id"),
                client_secret=raw_credentials.get("client_secret"),
                )
                # credentials = Credentials(**calendar_connection.credentials)
                service = build('calendar', 'v3', credentials=credentials)
               
                event = {
                    "summary": summary,
                    "description": description,
                    "start": {"dateTime": start_time, "timeZone": "UTC"},
                    "end": {"dateTime": end_time, "timeZone": "UTC"},
                    "attendees": [{"email": attendees}],
                    # "attendees": [{"email": 'dilbarh2@gmail.com'}],
                }
                calendar_event = service.events().insert(calendarId='primary', body=event).execute()

                # Save event details to the database
                saved_event = GoogleCalendarEvent.objects.create(
                    summary=summary,
                    start_time=start_time,
                    end_time=end_time,
                    description=description,
                    attendees=attendees,
                    calendar_event_id=f"{calendar_event['id']}",  # Access event ID as string
                    calendar_link=calendar_event['htmlLink'],  # Use htmlLink for the event URL
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
            print(f"Error occurred: {str(e)}")
            return JsonResponse({"status": "error", "message": f"Error occurred: {str(e)}"}, status=400)

    # Handle non-POST requests
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)


  
