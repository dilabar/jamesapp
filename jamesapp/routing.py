from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/play_ai/<int:user_id>/<str:agent_id>/', consumers.TwilioToPlayAIStreamConsumer.as_asgi()),
]
    