import json
import base64
import logging
import threading
from django.shortcuts import get_object_or_404
from websocket import create_connection, WebSocketConnectionClosedException
from django.conf import settings
from agent.models import Agent, PhoneCall, ServiceDetail
from jamesapp.utils import decrypt
from channels.generic.websocket import WebsocketConsumer

logger = logging.getLogger(__name__)


class TwilioToPlayAIStreamConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream_id = None
        self.play_ai_ws = None
        self.play_ai_connected = False
        self.twilio_connected = False
        self.call_sid = None
        self.user_id = None
        self.conversationId = None
        self.agnt_id = None
        self.initial_prompt_sent = False
        self.conversation_started = False

    def connect(self):
        logger.info("Connecting...")
        self.accept()

        # Retrieve URL route parameters
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.call_sid = self.scope["url_route"]["kwargs"]["call_sid"]
        self.agnt_id = self.scope["url_route"]["kwargs"]["agnt_id"]

        # Fetch Play.ai service details
        play_ai_service = ServiceDetail.objects.filter(
            user_id=self.user_id, service_name='play_ai'
        ).first()

        if play_ai_service:
            try:
                agobj=get_object_or_404(Agent, id=self.agnt_id)
                print(agobj.decrypted_agent_id)
                agent_id = agobj.decrypted_agent_id
                play_ai_url = f"wss://api.play.ai/v1/talk/{agent_id}"
                self.play_ai_ws = create_connection(play_ai_url)

                # Send setup message to Play.ai
                self.play_ai_ws.send(json.dumps({
                    "type": "setup",
                    "inputEncoding": "mulaw",
                    "inputSampleRate": 8000,
                    "outputFormat": "mulaw",
                    "outputSampleRate": 8000,
                    "apiKey": play_ai_service.decrypted_api_key,
                    "prompt": f"Hidden prompt with Call SID: {self.call_sid}, keep it for future use when action call"
                }))

                logger.info("Connected to Play.ai WebSocket")
                self.play_ai_connected = True

                # Start thread to listen for Play.ai responses
                threading.Thread(target=self.handle_play_ai_response, daemon=True).start()

            except Exception as e:
                logger.error(f"Failed to connect to Play.ai WebSocket: {e}")
                self.close()
        else:
            logger.error("Play.ai credentials not found for user")
            self.close()

    def receive(self, text_data):
        try:
            twilio_data = json.loads(text_data)
            event_type = twilio_data.get('event')

            if event_type == 'connected':
                self.twilio_connected = True
                logger.info("Twilio connected")
            elif event_type == "media":
                self.stream_id = twilio_data.get('streamSid')
                audio_payload = twilio_data["media"].get("payload")

                if audio_payload and self.conversation_started:
                    audio_data_bytes = base64.b64decode(audio_payload)
                    play_ai_message = {
                        "type": "audioIn",
                        "data": base64.b64encode(audio_data_bytes).decode('ascii'),
                    }
                    self.play_ai_ws.send(json.dumps(play_ai_message))
                elif not self.conversation_started:
                    logger.warning("Received audio before Play.ai conversation started")
            elif event_type == 'stop':
                logger.info("Twilio stream stopped")
        except Exception as e:
            logger.error(f"Error handling stream data: {e}")

    def handle_play_ai_response(self):
        try:
            while True:
                play_ai_response = self.play_ai_ws.recv()
                play_ai_data = json.loads(play_ai_response)

                response_type = play_ai_data.get("type")
                if response_type == "init":
                    self.conversationId = play_ai_data.get("conversationId")
                    self.conversation_started = True

                    PhoneCall.objects.filter(twilio_call_id=self.call_sid).update(
                        play_ai_conv_id=self.conversationId,
                        agent_owner_id=play_ai_data.get("agentOwnerId"),
                        recording_presigned_url=play_ai_data.get("recordingPresignedUrl"),
                        agnt_id=self.agnt_id
                    )
                elif response_type == "onAgentTranscript":
                    msg = play_ai_data.get("message")
                    logger.info(f"Transcript from Play.ai: {msg}")
                elif response_type == "audioStream":
                    audio_data = play_ai_data.get("data")
                    if audio_data:
                        self.send_audio_to_twilio(audio_data)
                elif response_type == "hangup":
                    ended_by = play_ai_data.get("endedBy")
                    logger.error(f"Play.ai hangup, ended by: {ended_by}")
                    self.send(text_data=json.dumps({
                        "event": "hangup",
                        "message": f"Call ended by: {ended_by}"
                    }))
                    self.close()
                    break
                elif response_type == "error":
                    logger.error(f"Error: {play_ai_data.get('code')} - {play_ai_data.get('message')}")
                    self.close()
                    break
        except WebSocketConnectionClosedException:
            logger.error("Play.ai WebSocket closed unexpectedly")
            self.close()
        except Exception as e:
            logger.error(f"Error receiving Play.ai response: {e}")

    def send_audio_to_twilio(self, audio_data):
        try:
            if self.twilio_connected and self.stream_id:
                encoded_audio = base64.b64encode(base64.b64decode(audio_data)).decode('ascii')
                self.send(json.dumps({
                    "event": "media",
                    "streamSid": self.stream_id,
                    "media": {
                        "payload": encoded_audio
                    }
                }))
                logger.info("Sent audio data to Twilio")
            else:
                logger.warning("Twilio not connected or Stream ID missing. Cannot send audio")
        except Exception as e:
            logger.error(f"Error sending audio to Twilio: {e}")

    def disconnect(self, close_code):
        if self.play_ai_ws:
            self.play_ai_ws.close()
            logger.info("Closed Play.ai WebSocket")
