from base64 import urlsafe_b64encode
import pandas as pd
from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from agent.models import Agent, PhoneCall, ServiceDetail
from contact.models import Campaign
from jamesapp.utils import decrypt, fetch_data_from_api
from twilio.rest import Client
import json
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse, Start, Stream,Connect,Dial,Gather
from django.conf import settings

from django.contrib import messages
import logging
logger = logging.getLogger(__name__)


# Twilio API credentials

@login_required
def call_initiate(request, agnt_id):
    # Fetch Twilio service details
    if request.user.is_agency():
        # Show agents for the agency and all its sub-accounts
        user=request.user
        campaigns = Campaign.objects.filter(user__in=user.get_all_subaccounts())  # Agency campaigns
        print(campaigns)
    else:
        # Show only the logged-in user's agents
        user=request.user.parent_agency
        campaigns = Campaign.objects.filter(user=request.user)  # Subaccount campaigns



    print(campaigns)
        
        
    twilio = ServiceDetail.objects.filter(user=user, service_name='twilio').first()
    if not twilio:
        return HttpResponse("Twilio service details not found.")

    client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)

    if request.method == "POST":
        phone_number = request.POST.get('phone_number')
        file_upload = request.FILES.get('file_upload')
        campaign_id = request.POST.get('campaign')

                # Fetch the selected campaign if provided
        selected_campaign = None
        if campaign_id:
            selected_campaign = Campaign.objects.filter(id=campaign_id, user__in=user.get_all_subaccounts()).first()

        # Manual entry handling
        if phone_number:
            phone_call = PhoneCall.objects.create(
                phone_number=phone_number,
                call_status='pending',
                user=request.user,
                agnt_id=agnt_id,
                campaign=selected_campaign,
            )
            try:
                call = client.calls.create(
                    url=f'{request.scheme}://{request.get_host()}/call/start_twilio_stream/{user.id}/{agnt_id}/',
                    to=phone_call.phone_number,
                    from_=twilio.decrypted_twilio_phone,
                    record=True,
                    method='POST',
                    status_callback=f'{request.scheme}://{request.get_host()}/call/call_status_callback/{phone_call.id}/',
                    status_callback_method='POST',
                    status_callback_event=["initiated", "ringing", "answered", "completed"],
                    # transcribe=True,
                    # transcribe_callback=f'https://{request.get_host()}/call/transcription_callback/{phone_call.id}/'
                    
                
                    
                )
                phone_call.call_status = 'initiated'
                phone_call.twilio_call_id = call.sid
                phone_call.save()
                messages.success(request, f"Call initiated successfully for {phone_number}.")
            except Exception as e:
                phone_call.call_status = 'failed'
                phone_call.save()
                messages.error(request, f"Error initiating call to {phone_number}: {str(e)}")
            # return redirect('callapp:initiate_call')

        # CSV/Excel upload handling
        elif file_upload:
            ext = file_upload.name.split('.')[-1].lower()
            try:
                # Read the uploaded file
                if ext == 'csv':
                    data = pd.read_csv(file_upload)
                elif ext in ['xls', 'xlsx']:
                    data = pd.read_excel(file_upload)
                else:
                    messages.error(request, "Unsupported file format. Please upload a CSV or Excel file.")
                    return redirect('callapp:initiate_call')

                initiated, failed = [], []
                # Iterate over rows and initiate calls
                for _, row in data.iterrows():
                    phone = row.get('Mobile') or row.get('mobile')
                    if pd.notna(phone):
                        phone = str(phone).strip()
                        if phone:
                            phone_call = PhoneCall.objects.create(
                                phone_number=phone,
                                call_status='pending',
                                user=request.user,
                                agnt_id=agnt_id,
                                campaign=selected_campaign
                            )
                            try:
                                call = client.calls.create(
                                    url=f'{request.scheme}://{request.get_host()}/call/start_twilio_stream/{user.id}/{agnt_id}/',
                                    to=phone_call.phone_number,
                                    from_=twilio.decrypted_twilio_phone,
                                    record=True,
                                    method='POST',
                                    status_callback=f'{request.scheme}://{request.get_host()}/call/call_status_callback/{phone_call.id}/',
                                    status_callback_event=["initiated", "ringing", "answered", "completed"],
                                    status_callback_method='POST',
                                    # transcribe=True,
                                    # transcribe_callback=f'https://{request.get_host()}/call/transcription_callback/{phone_call.id}/'
                                    

                                )
                                phone_call.call_status = 'initiated'
                                phone_call.twilio_call_id = call.sid
                                phone_call.save()
                                initiated.append(phone)
                            except Exception as e:
                                phone_call.call_status = 'failed'
                                phone_call.save()
                                failed.append(phone)

                # Display success and failure messages
                if initiated:
                    messages.success(request, f"Calls initiated successfully for: {', '.join(initiated)}.")
                if failed:
                    messages.error(request, f"Failed to initiate calls for: {', '.join(failed)}.")

            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                return redirect('callapp:initiate_call')

    return render(request, 'callapp/start_calling.html',{'campaigns': campaigns})
@login_required
def start_calling(request):
    return render(request, 'callapp/start_calling.html')
@login_required
def start_card(request):
    # agents = Agent.objects.filter(user =request.user)  # Fetch all agents from the database
    if request.user.is_agency():
        # Show agents for the agency and all its sub-accounts
        agents = Agent.objects.filter(user=request.user)
    else:
        # Show only the logged-in user's agents
        agents = Agent.objects.filter(user=request.user.parent_agency)
        
    context={
        'agents': agents
    }
    return render(request, 'callapp/agent_card.html',context)
   
@csrf_exempt
def start_twilio_stream(request, user_id,agnt_id):
    if request.method == 'POST':
        call_sid = request.POST.get('CallSid')
    else:
        call_sid = request.GET.get('CallSid')


    if call_sid:
        print(f"Received CallSid: {call_sid}")
    else:
        print("No CallSid found in the request")
    response = VoiceResponse()
    
    # Define your WebSocket URL to receive the Twilio stream data
    stream_url = f"wss://{request.get_host()}/ws/play_ai/{user_id}/{agnt_id}/{call_sid}/"
    try:
     

        # Append the dial and conference to the response
        connect = Connect()
        connect.stream(name='Twilio Stream', url=stream_url)

        response.append(connect)
        # # Optional: Play an initial message or beep
        # response.say('The stream has started. You may now begin speaking.')
        
    except Exception as e:
        logger.error(f"Error starting Twilio stream: {str(e)}")
        response.say("Error starting the audio stream. Please try again later.")
    
    return HttpResponse(str(response), content_type="text/xml")
@csrf_exempt
def transcription_callback(request, id):
    if request.method == 'POST':
        transcription_text = request.POST.get('TranscriptionText')
        transcription_sid = request.POST.get('TranscriptionSid')
        
        # You can save the transcription text to your model or process it
        if transcription_text:
            logger.info(f"Transcription for CallSid {id}: {transcription_text}")
            # Save transcription text to your database
            lg = PhoneCall.objects.filter(id=id).first()
            if lg:
                lg.transcription_text = transcription_text
                lg.save()
            else:
                logger.error(f"No phone call found with Call SID: {id}")

        return HttpResponse("Transcription received", status=200)

    return HttpResponse("Invalid request", status=400)
# @csrf_exempt
# def start_twilio_stream(request, user_id, agent_id):
#     """
#     Starts Twilio streaming for Play.ai and connects to the conference.
#     """
#     if request.method == 'POST':
#         call_sid = request.POST.get('CallSid')
#     else:
#         call_sid = request.GET.get('CallSid')
#     response = VoiceResponse()

#     # Define the WebSocket URL for Play.ai
#     stream_url = f"wss://{request.get_host()}/ws/play_ai/{user_id}/{agent_id}/"

#     try:
#         # Connect Play.ai to the conference
#         connect = Connect()
#         connect.stream(name="PlayAI_Stream", url=stream_url)

#         # Join Play.ai to the conference
#         dial = Dial()
#         dial.conference(
#             "PlayAI_Conference",  # Same conference name
#             start_conference_on_enter=True,
#             end_conference_on_exit=False,
#         )
#         response.append(connect)
#         response.append(dial)

#     except Exception as e:
#         logger.error(f"Error starting Twilio stream for Play.ai: {e}")
#         response.say("Error starting the stream. Please try again later.")

#     return HttpResponse(str(response), content_type="text/xml")


# @csrf_exempt
# def transfer_call(request, phone_number):
#     """
#     This view is used to transfer the call to a real agent using Twilio's <Dial> verb.
#     """
#     print("The Action is working",request.GET)

#     response = VoiceResponse()
    
#     # Inform the caller about the transfer
#     response.say("Please hold while we transfer you to a real agent.")

#     # Dial the specified phone number (the real agent)
#     response.dial(phone_number)

#     return HttpResponse(str(response), content_type="text/xml")
# @csrf_exempt
# def transfer_call(request, phone_number):
#     """
#     Transfers the call to a real agent and listens for DTMF inputs to perform actions.
#     """
#     response = VoiceResponse()

#     # Inform the caller about the transfer
#     response.say("Please hold while we transfer you to a real agent.")

#     # Dial the agent and include a gather block
#     dial = response.dial()
#     dial.number(
#         phone_number,
#         # url=f"https://{request.get_host()}/call/agent_dtmf_gather/new/"
#     )

#     # Append the dial block to the response
#     response.append(dial)

#     # Return the TwiML response
#     return HttpResponse(str(response), content_type="text/xml")
@csrf_exempt
def transfer_call(request, phone_number,cal_sid):
    """
    Transfers the call to a real agent using a conference so that Play.ai can remain in the call.
    """
    # lg = PhoneCall.objects.filter(twilio_call_id=cal_sid).first()


    # Assume that the summary is available in the PhoneCall object or passed in the request body
    # summary = lg.hand_off_summary if lg.hand_off_summary else "No summary available."
    response = VoiceResponse()

    # Inform the caller about the transfer
    response.say("You are being transferred to a real agent. Please stay on the line.")
       # Create a unique conference name based on the Call SID
    logger.info("Caller informed about transfer.")

    # Create a unique conference name
    conf_name = f"Conference_{cal_sid}"
    logger.info(f"Conference name: {conf_name}")

    # Add the caller to the conference
    response.dial().conference(
        conf_name,
        start_conference_on_enter=True,
        end_conference_on_exit=False
    )
    logger.info("Caller added to the conference.")
 
     # Add the caller to the conference as well
    response.say("You are now in a conference with the agent.", voice='alice', language='en')
    # response.record(transcribe=True, transcribe_callback=f'https://{request.get_host()}/call/transcription_callback/{cal_sid}/')

    # response.pause(length=3)



    # Return the TwiML response
    return HttpResponse(str(response), content_type="text/xml")
@csrf_exempt
def call_status_callback(request,id):
    if request.method == 'POST':
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        recording_url = request.POST.get('RecordingUrl')
        recording_sid = request.POST.get('RecordingSid')
        call_duration = request.POST.get('CallDuration')
        recording_duration = request.POST.get('RecordingDuration')
        caller = request.POST.get('Caller')
        called = request.POST.get('Called')
        direction = request.POST.get('Direction')
        from_country = request.POST.get('FromCountry')
        to_country = request.POST.get('ToCountry')
        from_city = request.POST.get('FromCity')
        to_city = request.POST.get('ToCity')
        transcription_text = request.POST.get('TranscriptionText')
    else:
        call_sid = request.GET.get('CallSid')
        call_status = request.GET.get('CallStatus')
        recording_url = request.GET.get('RecordingUrl')
        recording_sid = request.GET.get('RecordingSid')
        call_duration = request.GET.get('CallDuration')
        recording_duration = request.GET.get('RecordingDuration')
        caller = request.GET.get('Caller')
        called = request.GET.get('Called')
        direction = request.GET.get('Direction')
        from_country = request.GET.get('FromCountry')
        to_country = request.GET.get('ToCountry')
        from_city = request.GET.get('FromCity')
        to_city = request.GET.get('ToCity')
        transcription_text = request.GET.get('TranscriptionText')
    lg = PhoneCall.objects.filter(id=id,twilio_call_id=call_sid).first()
    if not lg:
        logger.error(f"No phone call found with Call SID: {call_sid}")
        return HttpResponse("Call not found.", status=404)

    lg.caller = caller
    lg.called = called
    lg.direction = direction
    lg.from_country = from_country
    lg.to_country = to_country
    lg.from_city = from_city
    lg.to_city = to_city

    if call_status =='initiated':
        logger.info(f"Call {call_sid} initiated.")
        pass
    elif call_status =='ringing':
        logger.info(f"Call {call_sid} is ringing.")
        lg.call_status='ringing'
        lg.save()
        pass
    elif call_status =='answered':
        logger.info(f"Call {call_sid} was answered.")
        lg.call_status='answered'
        lg.save()
        pass
    elif call_status =='completed':
        logger.info(f"Call {call_sid} completed.")
        lg.recording_url = recording_url
        lg.recording_sid = recording_sid
        lg.call_duration = call_duration if call_duration else None
        lg.recording_duration = recording_duration if recording_duration else None
        lg.transcription_text=transcription_text if transcription_text else None
        lg.call_status='completed'
        lg.save()

    else:
        lg.call_status=call_status
        lg.save()


    return HttpResponse("Call record updated successfully.", status=200)
    # return HttpResponse("Invalid request method.", status=405)
@csrf_exempt
def join_conference(request):
    """
    Once the agent picks up, they are added to the conference and receive a summary.
    """
    call_sid = request.GET.get("CallSid")
    response = VoiceResponse()

    # Retrieve the call information from the database using the CallSid
    lg = PhoneCall.objects.filter(twilio_call_id=call_sid).first()

    if not lg:
        return HttpResponse("Call not found.", status=404)

    # Assume that the summary is available in the PhoneCall object
    summary = lg.hand_off_summary if lg.hand_off_summary else "No summary available."

    # Announce the summary to the agent after they join the conference
    response.say(f"Agent, here is the call summary: {summary}", voice='alice', language='en')

    # Return the TwiML response to Twilio
    return HttpResponse(str(response), content_type="text/xml")
@csrf_exempt
def forward_call(request):
    """
    This view is used to transfer a call to a real agent using Twilio's <Dial> verb.
    """
    print("The Action is working forward_call",request.GET.get('call_sid'),request.body )
    body_data = json.loads(request.body)
    summary = body_data.get('data')
    # Retrieve the Call SID from the request query parameters
    cal_sid = request.GET.get('call_sid')
    if not cal_sid:
        logger.error("No Call SID provided in the request.")
        return HttpResponse("Call SID is missing.", status=400)

    # Fetch the PhoneCall instance using the Call SID
    lg = PhoneCall.objects.filter(twilio_call_id=cal_sid).first()
    if not lg:
        logger.error(f"No phone call found with Call SID: {cal_sid}")
        return HttpResponse("Call not found.", status=404)

    # Decrypt agent_id and fetch agent data
    try:
        agg=lg.agnt
        print(agg)
        print(lg.user)
        agent = Agent.objects.filter(id=agg.id, user=lg.user).first()
        if not agent:
            logger.error(f"Agent with ID {lg.agent_id} not found.")
            return HttpResponse("Agent not found.", status=404)
    except Exception as e:
        logger.error(f"Error decrypting agent ID: {e}")
        return HttpResponse("Error processing agent data.", status=500)

    # Fetch Twilio service credentials
    twilio_service = ServiceDetail.objects.filter(user=lg.user, service_name='twilio').first()
    if not twilio_service:
        logger.error(f"Twilio service credentials not found for user {lg.user}.")
        return HttpResponse("Twilio service credentials missing.", status=404)

    try:
        # Initialize Twilio client with decrypted credentials
        client = Client(twilio_service.decrypted_account_sid, twilio_service.decrypted_api_key)
        # # Construct the transfer URL with the real agent's phone number
        transfer_url = f"https://{request.get_host()}/call/transfer_call/{agent.real_agent_no}/{cal_sid}/"

        # # Update the call with the transfer URL to redirect the call
        call = client.calls(cal_sid).update(url=transfer_url, method="POST")
        # Now dial the agent and add them to the same conference
        conf_name = f"Conference_{cal_sid}"
        
            
        phone_call = PhoneCall.objects.create(
                                phone_number=agent.real_agent_no,
                                call_status='pending',
                                user=lg.user,
                                from_call_id=lg
                            )
        agent_call = client.calls.create(
            to=agent.real_agent_no,  # Agent's phone number
            from_=twilio_service.decrypted_twilio_phone,  # Your Twilio number
            twiml=f"""
            <Response>
                <Say>{summary}</Say>
                <Dial>
                    <Conference startConferenceOnEnter="true" endConferenceOnExit="false">
                        {conf_name}
                    </Conference>
                </Dial>
            </Response>
            """,
           
            status_callback=f"https://{request.get_host()}/call/call_status_callback/{phone_call.id}/",  # Your status callback URL
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            status_callback_method="POST"
        )
        phone_call.call_status='initiated'
        phone_call.twilio_call_id=agent_call.sid
        # Update the call status to indicate the call has been forwarded to the real agent
        lg.hand_off_summary=summary
        lg.call_status = 'Forwarded'
        lg.is_call_forwarded = True  # Optionally track that the call was forwarded
        lg.save()
        phone_call.save()

        logger.info(f"Call {cal_sid} successfully redirected to agent {agent.real_agent_no}")
        return HttpResponse("Call transferred to real agent.",status=200)

    except Exception as e:
        logger.error(f"Error transferring call {cal_sid}: {e}")
        return HttpResponse("Failed to transfer the call.", status=500)

@csrf_exempt
def handle_dtmf_input(request, cal_sid):
    """
    This function handles the DTMF input after the user presses a key during the conference.
    Based on the digit, different actions like transferring the call or adding participants will be performed.
    """
    response = VoiceResponse()

    # Get the digits pressed by the user
    digits = request.POST.get('Digits')

    if digits:
        if digits == '1':
            response.say("Transferring you to another agent.")
            # Logic to transfer the call to another agent
            # You can call an agent's phone number or direct to another conference
            response.dial('919954634102')
        elif digits == '2':
            response.say("You pressed 2. Adding another participant.")
            # Logic to add another participant
            response.dial().conference(f"Conference_Call_{cal_sid}",start_conference_on_enter=True)
        else:
            response.say("Invalid input. Please try again.")
            response.redirect(f"/call/start_conference/{cal_sid}/")  # Redirect back to start conference for retry
    else:
        # Default message if no DTMF input is received
        response.say("No input received. You are still in the conference.")
        response.redirect(f"/call/conference_dtmf_url/{cal_sid}/")  # Redirect back to start conference

    return HttpResponse(str(response), content_type="text/xml")
@csrf_exempt
def conference_dtmf_url(request, cal_sid):
    """
    This function starts a conference and prompts the user for DTMF input.
    """
    response = VoiceResponse()

    # Create a <Gather> element to listen for DTMF input
    gather = Gather(num_digits=1, action=f"/call/handle_dtmf_input/{cal_sid}/", timeout=10)

    # Prompt the user for input (e.g., press 1 for transfer, 2 to add a participant)
    gather.say("You are now in the conference call. Press 1 to transfer to another agent, press 2 to add another participant.")

    # If no input is received, we redirect the user back to this page to retry
    response.append(gather)
    response.redirect(f"/call/handle_dtmf_input/{cal_sid}/")

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

@csrf_exempt
def twilio_voice(request, user_id, agnt_id):
    """
    Handles Twilio webhook for voice and saves call details in PhoneCall model.
    """
    logger.info(f"Received call: request {request.POST}")
    if request.method == 'POST':
        # Extract details from the POST request
        call_sid = request.POST.get('CallSid')
        from_number = request.POST.get('From')
        to_number = request.POST.get('To')
        call_status = request.POST.get('CallStatus', 'initiated')

        # Log the received data
        logger.info(f"Received call: SID={call_sid}, From={from_number}, To={to_number}")

        try:
            PhoneCall.objects.update_or_create(
                twilio_call_id=call_sid,
                defaults={
                    'phone_number': from_number,
                    'call_status': call_status,
                    'user_id': user_id,
                    'agnt_id': agnt_id,
                },
            )
            logger.info(f"Call {call_sid} saved successfully.")
        except Exception as e:
            logger.error(f"Error saving call {call_sid}: {str(e)}")

    # Create Twilio VoiceResponse
    response = VoiceResponse()
    stream_url = f"wss://{request.get_host()}/ws/play_ai/{user_id}/{agnt_id}/{call_sid}/"

    try:
        # response.record(
        #     max_length=3600,  # Maximum recording length (in seconds)
        #     action=f"/twilio/recording_status/{call_sid}/",  # URL to handle recording completion
        #     method="POST",  # POST method to send data back
        #     timeout=10,  # Wait for silence timeout in seconds
        #     play_beep=True,  # Play a beep when starting the recording
        #     transcribe=False  # Set to True if you want automatic transcription of the recording
        # )
        connect = Connect()
        connect.stream(name='TwilioStream', url=stream_url)
        response.append(connect)
        response.say("Audio stream is now active. Please speak.")
    except Exception as e:
        logger.error(f"Error starting Twilio stream: {str(e)}")
        response.say("Error starting the audio stream. Please try again later.")

    return HttpResponse(str(response), content_type="text/xml")