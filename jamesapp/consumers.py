import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from websocket import create_connection
import requests

class PlayAIConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get agent_id from the URL route
        self.agent_id = self.scope['url_route']['kwargs']['agent_id']
        self.room_group_name = f'play_ai_{self.agent_id}'

        # Join WebSocket group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave WebSocket group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        audio_stream = text_data_json.get('audio_data')

        if audio_stream:
            # Send the audio data to Play.ai via WebSocket
            ws = create_connection(f"wss://api.play.ai/v1/talk/{self.agent_id}")
            ws.send(json.dumps({"type": "setup", "apiKey": settings.PLAY_AI_API_KEY}))

            try:
                ws.send(audio_stream)  # Send audio data to Play.ai

                # Receive the response and send it back to the WebSocket client (Twilio)
                while True:
                    response_data = ws.recv()
                    response_json = json.loads(response_data)

                    if 'response' in response_json:
                        play_audio_url = response_json['response']['audio']
                        await self.send(text_data=json.dumps({
                            'play_audio_url': play_audio_url
                        }))
                    elif 'end' in response_json:
                        break

            except Exception as e:
                await self.send(text_data=json.dumps({
                    'error': str(e)
                }))
            finally:
                ws.close()

