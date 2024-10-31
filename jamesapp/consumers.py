import json
import base64
from agent.models import ServiceDetail
from django.contrib.auth.decorators import login_required
from channels.generic.websocket import WebsocketConsumer
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
    @login_required
    def connect(self):
        self.accept()
        user = self.scope["user"]  # Retrieve the logged-in user
        play_ai_service = ServiceDetail.objects.filter(user=user, service_name='play_ai').first()
        if play_ai_service:
        # Decrypt the credentials

            try:
                agent_id = decrypt(self.scope["url_route"]["kwargs"]["agent_id"])
                
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
                }))
                
                logger.info("Connected to Play.ai WebSocket")
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
                
                # Handle Play.ai's response
                if play_ai_data.get("type") == "audioStream":
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
                    self.close()  # Close the WebSocket connection
                    break  # Exit the loop after hangup
        except WebSocketConnectionClosedException:
            logger.error("Play.ai WebSocket closed unexpectedly")
            self.close()
        except Exception as e:
            logger.error(f"Error receiving Play.ai response: {e}")

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

    def disconnect(self, close_code):
        # Clean up the Play.ai WebSocket on disconnect
        if self.play_ai_ws:
            self.play_ai_ws.close()
            logger.info("Closed Play.ai WebSocket")
