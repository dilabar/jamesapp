from django.urls import path
from .views import call_play_ai_api,agent_list

urlpatterns = [
    path('', agent_list, name='agent_list'),
    path('get-agent/<str:agent_id>/', call_play_ai_api, name='get_agent'),  # Updated to pass agent ID
]
