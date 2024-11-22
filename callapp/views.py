from base64 import urlsafe_b64encode
import pandas as pd
from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from agent.models import Agent, PhoneCall, ServiceDetail
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
                call_status='pending',
                user=request.user,
                
            )
            # Place the call
            try:
                call = client.calls.create(
                    url=f'{request.scheme}://{request.get_host()}/call/start_twilio_stream/{request.user.id}/{agent_id}/',
                    to=phone_call.phone_number,
                    from_=twilio.decrypted_twilio_phone,
                    record=True,
                    method='POST',
                    status_callback=f'{request.scheme}://{request.get_host()}/call/call_status_callback/{phone_call.id}/',
                    status_callback_method='POST',  # You can also use 'GET' if preferred
                    status_callback_event=["initiated", "ringing", "answered", "completed"],
                )
                print(f"call....{call}")
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
                            call_status='pending',
                            user=request.user
                        )
                        try:
                            call = client.calls.create(
                                url=f'{request.scheme}://{request.get_host()}/call/start_twilio_stream/{request.user.id}/{agent_id}/',
                                to=phone_call.phone_number,
                                from_=twilio.decrypted_twilio_phone,
                                record=True,
                                method='POST'
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
    stream_url = f"wss://{request.get_host()}/ws/play_ai/{user_id}/{agent_id}/{call_sid}/"
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



    # Return the TwiML response
    return HttpResponse(str(response), content_type="text/xml")
@csrf_exempt
def call_status_callback(request):
    if request.method == 'POST':
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        if call_status =='initiated':
            pass
        elif call_status =='ringing':
            pass
        elif call_status =='answered':
            pass
        elif call_status =='completed':
            pass
    return HttpResponse(status=200)
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
        agg=lg.agent_id
        print(agg)
        print(lg.user)
        agent = Agent.objects.filter(agent_id=agg, user=lg.user).first()
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
        print(f" host {request.get_host()}")
        # # Construct the transfer URL with the real agent's phone number
        transfer_url = f"https://{request.get_host()}/call/transfer_call/{agent.real_agent_no}/{cal_sid}/"

        # # Update the call with the transfer URL to redirect the call
        call = client.calls(cal_sid).update(url=transfer_url, method="POST")
        # Now dial the agent and add them to the same conference
        conf_name = f"Conference_{cal_sid}"

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
            status_callback=f"https://{request.get_host()}/call/call_status_callback/2/",  # Your status callback URL
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            status_callback_method="POST"
        )

        # Update the call status to indicate the call has been forwarded to the real agent
        lg.hand_off_summary=summary
        lg.call_status = 'Forwarded'
        lg.is_call_forwarded = True  # Optionally track that the call was forwarded
        lg.save()

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

