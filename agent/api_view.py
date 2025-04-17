from datetime import datetime, time, timedelta
from hashlib import sha256
import hashlib
import os
import random
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
import requests
from agent.forms import AgentFormV1
from twilio.rest import Client
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import urllib
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.db import transaction
from django.utils.timesince import timesince
from django.utils.timezone import now
from rateMaster.models import CallRate
from scheduling.models import CalendarConnection
from jamesapp.utils import analyze_conversation_log, decrypt, encrypt, get_transcript_data
from .models import Agent, Conversation, PhoneCall, ServiceDetail,GoogleCalendarEvent
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
def get_status_badge(status):
    status = status.lower()
    badge_class = {
        'initiated': 'primary',
        'completed': 'success',
        'ringing': 'warning',
        'failed': 'danger',
        'forwarded': 'secondary',
        'inprogress': 'info',
        'pending': 'light'
    }.get(status, 'dark')
    
    return f'''<span class="badge badge-{badge_class}">{status.capitalize()}</span>'''

@login_required
def call_history_data(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    if request.user.is_agency:
        user_queryset = request.user.get_all_subaccounts()
    else:
        user_queryset = [request.user]

    queryset = PhoneCall.objects.filter(user__in=user_queryset).select_related('agnt').order_by(F('timestamp').desc(nulls_last=True))

    if search_value:
        queryset = queryset.filter(
            Q(phone_number__icontains=search_value) |
            Q(twilio_call_id__icontains=search_value) |  # ✅ Corrected
            Q(agnt__display_name__icontains=search_value)|
            Q(call_status__icontains=search_value)  # ✅ Added search for call_status
        )

    total = queryset.count()
    calls = queryset[start:start + length]

    data = []
    for index, call in enumerate(calls, start=start + 1):
        bill = calculate_bill(call)  # Your custom logic
        timestamp = call.timestamp.strftime('%Y-%m-%d %H:%M:%S') if call.timestamp else 'N/A'
        time_ago = timesince(call.timestamp, now()) + " ago" if call.timestamp else 'N/A'
        data.append({
                'index': index,
                'agent': call.agnt.display_name.title() if call.agnt else 'N/A',
                'phone_number': call.phone_number,
                'call_sid': call.twilio_call_id,
                'duration': f"{call.call_duration // 60}m {call.call_duration % 60}s" if call.call_duration else '0m 0s',
                'timestamp': timestamp,
                'time_ago': time_ago,
                'bill': f"${bill:.2f}" if bill else '$0.00',
                'campaign_name': getattr(call, 'campaign_name', 'Demo').capitalize() if hasattr(call, 'campaign_name') else 'Demo',
                'customer_name': f"<a href='#'>{getattr(call, 'customer_name', 'NA').capitalize()}</a>" if hasattr(call, 'customer_name') else '<a href="#">NA</a>',
                'call_status_badge': get_status_badge(call.call_status or ''),
                'actions': f'''
                    <a href="{reverse('agent:call_detail', args=[call.id])}" class="btn btn-warning btn-sm mt-2">
                        Details
                    </a>
                '''
            })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': data
    })
@login_required
def call_detail(request, id):
    obj = PhoneCall.objects.filter(user=request.user, id=id).first()
    # obj = PhoneCall.objects.select_related('campaign').filter(user=request.user, id=id).first()
   
    if not obj:
        return render(request, 'new/error.html', {'message': 'Call not found'})  # Handle missing call object

    play_ai = ServiceDetail.objects.filter(user=request.user, service_name='play_ai').first()
    # print(obj.campaign.agent.agent_id)
    ag=decrypt(obj.campaign.agent.agent_id)
        # Check if the transcript is already available for this call
    transcript = None
    conversation, created = Conversation.objects.get_or_create(
        phone_call=obj
    )

    if conversation.transcript_available:
        # ✅ Transcript already available, no need to call API
        transcript = conversation.transcript_data

    else:
        # ❌ Transcript not available, fetch from external API
        data = get_transcript_data(
            ag, 
            obj.play_ai_conv_id, 
            play_ai.decrypted_api_key, 
            play_ai.decrypted_account_sid, 
            100, 0
        )
        if data:
            transcript = data
            # Format transcript for summary
            # transcript_text = "\n".join(
            #     [f"{item['role'].capitalize()}: {item['content']}" for item in data]
            # )

            # Generate AI summary (assumed to be a function)
            # summary = analyze_conversation_log(transcript_text)

            # Update or create the conversation record
            conversation.transcript_data = data
            conversation.transcript_available = True
            conversation.save()


    # Calculate end time
    if obj.timestamp and obj.call_duration:
        end_time = obj.timestamp + timedelta(seconds=obj.call_duration)
    else:
        end_time = None  # Handle invalid data
    # Prepare context
    context = {
        'call_obj': obj,
        'end_time': end_time,
        'transcript': transcript,
        'conversation_obj':conversation
    }
    return render(request, 'new/all_conversation_log.html', context)

@csrf_exempt
def analyze_call_summary(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            call_id = data.get("call_id")

            if not call_id:
                return JsonResponse({"error": "Missing call_id"}, status=400)

            conversation = Conversation.objects.get(phone_call_id=call_id)

            # If already summarized, return existing summary
            if conversation.ai_summary:
                return JsonResponse({"summary": conversation.ai_summary})

            # Generate transcript text
            transcript_text = "\n".join(
                [f"{item['role'].capitalize()}: {item['content']}" for item in conversation.transcript_data]
            )

            # Analyze and generate summary
            ai_summary = analyze_conversation_log(transcript_text)

            # Save the summary
            conversation.ai_summary = ai_summary
            conversation.save()

            return JsonResponse({"summary": ai_summary})

        except Conversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)
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
            attendees = data.get("attendees", [])

            agentId = data.get("agentId")
            agent_id_hash = hashlib.sha256(agentId.encode()).hexdigest()

            agd = Agent.objects.filter(agent_id_hash=agent_id_hash).first()
            if not agd:
                return JsonResponse({"status": "error", "message": "Agent not found"}, status=400)

            # Save event to the database first
            saved_event = GoogleCalendarEvent.objects.create(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                attendees=attendees,
                # calendar_event_id=None,  # Initially null
                # calendar_link=None,  # Initially null
                status="pending",  # Initially pending
            )

            # Try booking Google Calendar event
            try:
                user = agd.user  # Ensure the user is set correctly
                calendar_connection = CalendarConnection.objects.get(user_id=user)
                if calendar_connection.provider == "google":
                    raw_credentials = calendar_connection.credentials
                    credentials = Credentials(
                        token=raw_credentials.get("token"),
                        refresh_token=raw_credentials.get("refresh_token"),
                        token_uri=raw_credentials.get("token_uri"),
                        client_id=raw_credentials.get("client_id"),
                        client_secret=raw_credentials.get("client_secret"),
                    )
                    service = build("calendar", "v3", credentials=credentials)

                    event = {
                        "summary": summary,
                        "description": description,
                        "start": {"dateTime": start_time, "timeZone": "UTC"},
                        "end": {"dateTime": end_time, "timeZone": "UTC"},
                        "attendees": [{"email": email} for email in attendees],  # Handle multiple attendees
                    }
                    calendar_event = service.events().insert(calendarId="primary", body=event).execute()

                    # Update event in database with Google Calendar details
                    saved_event.calendar_event_id = calendar_event["id"]
                    saved_event.calendar_link = calendar_event["htmlLink"]
                    saved_event.status = "booked"
                    saved_event.save()

            except Exception as calendar_error:
                print(f"Google Calendar Error: {str(calendar_error)}")
                saved_event.status = "failed"
                saved_event.save()

            # Respond with success and event details
            return JsonResponse({
                "status": "success",
                "message": "Event processed.",
                "event": {
                    "id": saved_event.id,
                    "summary": saved_event.summary,
                    "start_time": saved_event.start_time,
                    "end_time": saved_event.end_time,
                    "calendar_link": saved_event.calendar_link,
                    "status": saved_event.status,  # Indicate booking success/failure
                },
            })

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return JsonResponse({"status": "error", "message": f"Error occurred: {str(e)}"}, status=400)

    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=405)
class AgentCreateView(View):
    def get(self, request):
        form = AgentFormV1()

        return render(request, 'agent/agent_create.html', {'form': form})

    def post(self, request):
        form = AgentFormV1(request.POST,user=request.user)
        if form.is_valid():
            print("valid")
        
            agent = form.save(commit=False)
            
            # Prepare API request
            url = "https://api.play.ai/api/v1/agents"
            payload = {
                "voice": agent.voice,
                "voiceSpeed": agent.voice_speed,
                "ttsModel": agent.llm_model,
                "displayName": agent.display_name,
                "description": agent.description,
                "greeting": agent.greeting,
                "prompt": agent.prompt,
                "criticalKnowledge": agent.critical_knowledge,
                "visibility": agent.visibility,
                "answerOnlyFromCriticalKnowledge": agent.answer_only_from_critical_knowledge,
                # "avatarPhotoUrl": agent.avatar_photo_url,
                # "criticalKnowledgeFiles": agent.critical_knowledge_files,
                # "phoneNumbers": agent.phone_numbers,
                "actions": []
            }

            headers = {
                "content-type": "application/json",
                "Authorization": "Bearer ak-524c684b1aa44488b66087078dd9efc0",
                "X-USER-ID": "kXeov3rz8WZD6FEAKs2i2UrUbtb2"
            }
            response = requests.post(url, json=payload, headers=headers)
            print(response.json())
            if response.status_code == 201:
                response_json = response.json()
                if response_json.get("id", agent.agent_id):
                    agent.agent_id_hash = hashlib.sha256(response_json.get("id", agent.agent_id).encode()).hexdigest()
                    agent.agent_id = encrypt(response_json.get("id", agent.agent_id))  # 🔐 Encrypt agent_id
                    # agent.agent_id = response_json.get("id", agent.agent_id)
                agent.voice = response_json.get("voice", agent.voice)
                agent.voice_speed = response_json.get("voiceSpeed", agent.voice_speed)
                agent.display_name = response_json.get("displayName", agent.display_name)
                agent.description = response_json.get("description", agent.description)
                agent.greeting = response_json.get("greeting", agent.greeting)
                agent.prompt = response_json.get("prompt", agent.prompt)
                agent.critical_knowledge = response_json.get("criticalKnowledge", agent.critical_knowledge)
                agent.visibility = response_json.get("visibility", agent.visibility)
                agent.avatar_photo_url = response_json.get("avatarPhotoUrl", agent.avatar_photo_url)
                agent.critical_knowledge_files = response_json.get("criticalKnowledgeFiles", agent.critical_knowledge_files)
                agent.phone_numbers = response_json.get("phoneNumbers", agent.phone_numbers)
                # agent.actions = response_json.get("actions", agent.actions)
                agent.response_data = response_json
                agent.save()
                
                return redirect('agent:agent_list')
            else:
                return JsonResponse({"error": "API request failed", "status_code": response.status_code}, status=400)
    
        # 🚨 Debug: Print form errors
        print("Form errors:", form.errors)  # Print errors in the terminal
        return JsonResponse({"error": "Invalid form data", "errors": form.errors}, status=400)

