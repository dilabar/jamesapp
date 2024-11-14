import json
import base64
from agent.models import Agent, PhoneCall, ServiceDetail
from django.contrib.auth.decorators import login_required
from channels.generic.websocket import WebsocketConsumer
from twilio.rest import Client
from jamesapp.utils import decrypt
from websocket import create_connection, WebSocketConnectionClosedException
import logging
import threading
from django.conf import settings

logger = logging.getLogger(__name__)

class TwilioToPlayAIStreamConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_id = None  # Initialize stream_id to store it when the stream starts
        self.play_ai_ws = None  # Initialize Play.ai WebSocket connection
        self.play_ai_connected = False  # Flag to track Play.ai connection status
        self.twilio_connected = False  # Flag to track twilio connection status
        self.call_sid=None
        self.user_id=None
        self.conversationId=None
        self.agent_id=None
        self.initial_prompt_sent = False
    def connect(self):
        logger.info("Connecting.....")

        self.accept()
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.call_sid = self.scope["url_route"]["kwargs"]["call_sid"]
        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        # user = self.scope["user"]  # Retrieve the logged-in user
        play_ai_service = ServiceDetail.objects.filter(user_id=self.user_id,service_name='play_ai').first()
        if play_ai_service:
        # Decrypt the credentials

            try:
                agent_id = decrypt(self.agent_id)
                
                play_ai_url = f"wss://api.play.ai/v1/talk/{agent_id}"
                self.play_ai_ws = create_connection(play_ai_url)
                
                # Send setup message to start conversation with Play.ai
                self.play_ai_ws.send(json.dumps({
                    "type": "setup",
                    "inputEncoding": "mulaw",
                    "inputSampleRate": 8000,
                    "outputFormat": "mulaw",
                    "outputSampleRate": 8000,
                    "apiKey": play_ai_service.decrypted_api_key,
                    "prompt": f"Hidden prompt with Call SID: {self.call_sid},keep it it for feture use when action call"
                   
                }))
                
                logger.info("Connected to Play.ai WebSocket")
                self.play_ai_connected = True
                # Start a thread to listen for Play.ai responses
                threading.Thread(target=self.handle_play_ai_response, daemon=True).start()
            except Exception as e:
                logger.error(f"Failed to connect to Play.ai WebSocket: {e}")
                self.close()
        else:
            logger.error("Twilio credentials not found for user")
            self.close()
  

    def receive(self, text_data):
        try:
            # Receive Twilio stream data
            twilio_data = json.loads(text_data)

            # Handle Twilio events
            event_type = twilio_data.get('event')
            if event_type == 'connected':
                self.twilio_connected = True
                logger.info("Twilio connected")
                # Send initial prompt once both connections are established
                # self.send_initial_prompt_if_ready()
            
            elif event_type == "media":
                # Extract audio payload from Twilio stream
                self.stream_id = twilio_data.get('streamSid')  # Updated to use 'streamSid'
                audio_payload = twilio_data["media"].get("payload", None)

                if audio_payload:
                    # Convert the audio payload to bytes and then to base64
                    audio_data_bytes = base64.b64decode(audio_payload)
                    play_ai_message = {
                        "type": "audioIn",
                        "data": base64.b64encode(audio_data_bytes).decode('ascii'),  # Encode as base64
                    }
                    self.play_ai_ws.send(json.dumps(play_ai_message))
                else:
                    logger.error("No audio payload found in Twilio data")

            elif event_type == 'stop':
                logger.info("Twilio stream stopped")
        except Exception as e:
            logger.error(f"Error handling stream data: {e}")

    def handle_play_ai_response(self):
        try:
            while True:
                play_ai_response = self.play_ai_ws.recv()
                play_ai_data = json.loads(play_ai_response)
                print(f".....{play_ai_data.get('type')}......")
                # Handle Play.ai's response
              
                if play_ai_data.get("type")== "init":
                    self.conversationId=play_ai_data.get("conversationId")
                    # Update PhoneCall model with conversationId
                    PhoneCall.objects.filter(twilio_call_id=self.call_sid).update(
                        play_ai_conv_id=self.conversationId,
                        agent_owner_id=play_ai_data.get("agentOwnerId"),
                        recording_presigned_url=play_ai_data.get("recordingPresignedUrl"),
                        agent_id=self.agent_id
                        )
                elif play_ai_data.get("type")=="onAgentTranscript":
                    msg = play_ai_data.get("message")
                    logger.info(f"Transcript message from Play.ai: {msg}")

                elif play_ai_data.get("type") == "audioStream":
                    # Extract the audio data
                    audio_data = play_ai_data.get("data")
                    if audio_data:
                        # Send audio back to Twilio
                        self.send_audio_to_twilio(audio_data)
                    else:
                        logger.error("No audio data in Play.ai response")
                
                elif play_ai_data.get("type") == "hangup":
                    ended_by = play_ai_data.get("endedBy")
                    logger.error(f"Play.ai hangup detected, ended by: {ended_by}")
                    self.send(text_data=json.dumps({
                        "event": "hangup",
                        "message": f"The call was ended: {ended_by}"
                    }))
                    # self.transfer_call_to_real_agent('919679728063')

                    self.close()  # Close the WebSocket connection
                    break  # Exit the loop after hangup

             
                elif play_ai_data.get("type")=="error":
                    logger.error(f"error code {play_ai_data.get('code')} ....message {play_ai_data.get('message')}")
                    self.close()  # Close the WebSocket connection
                    break  # Exit the loop after hangup


        except WebSocketConnectionClosedException:
            logger.error("Play.ai WebSocket closed unexpectedly")
            self.close()
        except Exception as e:
            logger.error(f"Error receiving Play.ai response: {e}")

    def initiate_call_transfer(self, real_agent_phone_number):
        try:
            # Close the Play.ai connection
            if self.play_ai_ws:
                self.play_ai_ws.close()
                logger.info("Disconnected Play.ai for transfer to real agent")
                twilio = ServiceDetail.objects.filter(user_id=self.user_id, service_name='twilio').first()
                client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)
            # Send redirect event to Twilio with the transfer URL
            transfer_url = f"https://bd73-2405-201-800d-e867-48-c89d-21c6-c2dd.ngrok-free.app/call/transfer_call/{real_agent_phone_number}/"

            #transfer_url = f"{settings.SITE_URL}{reverse('transfer_to_real_agent', args=[real_agent_phone_number])}"
            # self.send(text_data=json.dumps({
            #     "event": "transfer_call",
            #     "redirect_url": transfer_url
            # }))
            call = client.calls(self.call_sid).update(url=transfer_url, method="POST")
            PhoneCall.objects.filter(twilio_call_id=self.call_sid).update(
                        is_call_forwarded=True,
                        call_status='Forwarded'
                        )
            self.close()
            logger.info("Twilio call redirected to real agent")
        except Exception as e:
            logger.error(f"Error transferring call to real agent: {e}")
    def send_audio_to_twilio(self, audio_data):
        """Send audio data to Twilio."""
        try:
            if not self.twilio_connected:
                logger.warning("Twilio connection not established. Cannot send audio data to Twilio.")
                return
            
            # Convert audio data to base64 if not already done
            encoded_audio = base64.b64encode(base64.b64decode(audio_data)).decode('ascii')

            # Send to Twilio
            self.send(json.dumps({
                "event": "media",
                "streamSid": self.stream_id,
                "media": {
                    "payload": encoded_audio
                }
            }))
            logger.info("Sent audio data to Twilio successfully")
        except Exception as e:
            logger.error(f"Error sending audio data to Twilio: {e}")
    def send_initial_prompt_if_ready(self):
        # Check if both connections are established and the initial prompt has not been sent
        if self.play_ai_connected and self.twilio_connected and not self.initial_prompt_sent:
            try:
                # Send hidden prompt with call_sid
                initial_prompt = {
                    "type": "textIn",
                    "data": f"please keep my call sid for future reference.Hidden prompt with Call SID: {self.call_sid}",
                }
                self.play_ai_ws.send(json.dumps(initial_prompt))
                self.initial_prompt_sent = True
                logger.info("Initial prompt sent to Play.ai")
            except Exception as e:
                logger.error(f"Error sending initial prompt: {e}")
    def disconnect(self, close_code):
        # Clean up the Play.ai WebSocket on disconnect
        if self.play_ai_ws:
            self.play_ai_ws.close()
            logger.info("Closed Play.ai WebSocket")
