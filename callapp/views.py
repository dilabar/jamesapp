import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse

from agent.models import PhoneCall
from twilio.rest import Client
import json
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.voice_response import VoiceResponse
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from websocket import create_connection


# Twilio API credentials

client = Client(settings.ACOUNT_SID, settings.AUTH_TOKEN)

def call_initate(request,agent_id):
    client = Client(settings.ACOUNT_SID, settings.AUTH_TOKEN)
    numbers_to_call = PhoneCall.objects.filter(call_status='pending')[:100]

    if not numbers_to_call:
        return HttpResponse("No pending calls found.")

    for phone_call in numbers_to_call:
        try:
            call = client.calls.create(
                url=f'http://{settings.ALLOWED_HOSTS[1]}/voice/{agent_id}/',
                to=phone_call.phone_number,
                from_=settings.TWILIO_PHONE_NUMBER
            )
            phone_call.call_status = 'pending'
            phone_call.save()
        except Exception as e:
            return HttpResponse(f"Error initiating call to {phone_call.phone_number}: {str(e)}")

    return HttpResponse("Calls initiated successfully!")
@csrf_exempt
def voice(request, agent_id):
    """
    Handles incoming voice requests from Twilio, and forwards the audio stream to Play.ai via WebSocket.
    """
    response = VoiceResponse()
    response.say("Hello, you are connected to your AI assistant.")

    # Prepare to send the audio to the WebSocket consumer
    audio_stream = request.POST.get('RecordingUrl', None)
    if audio_stream:
        audio_response = request.get(audio_stream)
        audio_bytes = audio_response.content

        # Forward the audio to the WebSocket
        ws_url = f"ws://{settings.ALLOWED_HOSTS[1]}/ws/play_ai/{agent_id}/"
        ws = create_connection(ws_url)
        ws.send(json.dumps({'audio_data': audio_bytes}))
        
        # Receive and play the AI response
        while True:
            play_response = ws.recv()
            response_json = json.loads(play_response)
            
            if 'play_audio_url' in response_json:
                play_audio_url = response_json['play_audio_url']
                response.play(play_audio_url)
            elif 'end' in response_json:
                break
            elif 'error' in response_json:
                return HttpResponse(f"Error during AI communication: {response_json['error']}")
        
        ws.close()

    response.say("Thank you for using our service.")
    return HttpResponse(str(response), content_type='text/xml')