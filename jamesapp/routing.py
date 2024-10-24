from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/play_ai/<str:agent_id>/', consumers.VoiceStreamConsumer.as_asgi()),
]
    