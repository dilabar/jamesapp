from django.urls import path
from .views import *
app_name='agent'
urlpatterns = [
    path('', agent_list, name='agent_list'),
    path('get-agent/<str:agent_id>/', call_play_ai_api, name='get_agent'),
    path('agent/', create_or_update_agent, name='create_agent'),  # For creating new agents
    path('agent/<str:agent_id>/', create_or_update_agent, name='update_agent'),  # For updating existing agents
    path('delete-agent/<str:agent_id>/', delete_agent, name='delete_agent'),
    path('get-conversation/<str:agent_id>/', get_conversation, name='get_conversation'),
    path('get-transcript/<str:agent_id>/<str:cid>/', get_transcript, name='get_transcript'),
    path('dashboards/', dashboards, name='dashboards'),
    path('login/', login, name='login'),
    path('signup/', signup, name='signup'),
    path('reset-password/', reset, name='reset'),
    path('logout/', logout, name='logout'), 
    path('play-ai-service/', service_detail_view, name='play_ai_service'),
    path('twilio-service/', twilio_service_detail_view, name='twilio_service'),
]
