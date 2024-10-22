import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse

from agent.models import PhoneCall
from .forms import UploadFileForm
from twilio.rest import Client
import json
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse
from django.conf import settings
from websocket import create_connection


# Twilio API credentials
account_sid = 'AC4fd638d826f7df2e6b19d7c0cd8be96f'
auth_token = 'e0d55fbb3bcc6b2c62b21e81e69d999c'
twilio_phone_number = '+19706333596'
client = Client(account_sid, auth_token)

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # Read the Excel file
            file = request.FILES['file']
            df = pd.read_excel(file)

            # Make calls to the numbers in the Excel file
            for index, row in df.iterrows():
                mobile_number = row['Mobile']
                call = client.calls.create(
                    twiml='<Response><Say>Hello, this is your AI assistant!</Say></Response>',
                    to=mobile_number,
                    from_=twilio_phone_number
                )
                print(f"Call initiated to {mobile_number}, SID: {call.sid}")

            return HttpResponse("Calls initiated successfully!")
    else:
        form = UploadFileForm()
    return render(request, 'callapp/upload.html', {'form': form})
def call_initate(request,agent_id):
    client = Client(account_sid, auth_token)
    numbers_to_call = PhoneCall.objects.filter(call_status='pending')[:100]

    if not numbers_to_call:
        return HttpResponse("No pending calls found.")

    for phone_call in numbers_to_call:
        try:
            call = client.calls.create(
                url=f'http://{settings.ALLOWED_HOSTS[0]}:8000/voice/{agent_id}/',
                to=phone_call.phone_number,
                from_=twilio_phone_number
            )
            phone_call.call_status = 'initiated'
            phone_call.save()
        except Exception as e:
            return HttpResponse(f"Error initiating call to {phone_call.phone_number}: {str(e)}")

    return HttpResponse("Calls initiated successfully!")

@csrf_exempt
def voice(request,agent_id):
    response = VoiceResponse()
    phone_number = request.POST.get('To', '')
    
    # Connect to Play.ai WebSocket
    ws = create_connection(f"wss://api.play.ai/v1/talk/{agent_id}")
    ws.send(json.dumps({"type": "setup", "apiKey": settings.PLAY_AI_API_KEY}))

    # Indicate the start of the conversation
    response.say("Hello, you are connected to your AI assistant.")
    
    # Create a placeholder for capturing audio
    audio_stream = []  # This will store the audio data

    # Start listening to audio input (this is a simulation, Twilio will send audio data)
    audio_data = request.POST.get('RecordingUrl')
    if audio_data:
        # Process the audio data from Twilio
        audio_response = request.get(audio_data)
        audio_bytes = audio_response.content
        
        # Send audio to Play.ai for processing
        ws.send(audio_bytes)

        # Receive a response from Play.ai
        while True:
            try:
                response_data = ws.recv()  # Blocking call to receive audio from Play.ai
                response_json = json.loads(response_data)

                # Process the Play.ai response here
                if 'response' in response_json:
                    play_audio_url = response_json['response']['audio']  # Get the audio URL to play back
                    response.play(play_audio_url)  # Play the audio response back to the caller
                elif 'end' in response_json:
                    break  # Exit the loop if the conversation ends
            except Exception as e:
                print(f"Error receiving data from Play.ai: {e}")
                break

    # Final response to the user
    response.say("Thank you for your time.")
    
    # Save feedback
    phone_call = PhoneCall.objects.get(phone_number=phone_number)
    phone_call.feedback = "Feedback from conversation"  # Replace with actual feedback logic
    phone_call.call_status = 'completed'
    phone_call.save()

    # Close WebSocket connection
    ws.close()

    return HttpResponse(str(response), content_type='text/xml')

