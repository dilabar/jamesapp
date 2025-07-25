from django.urls import path
from .views import *
from .api_view import *
app_name='agent'
urlpatterns = [
    path('', agent_list, name='agent_list'),
    path('get-agent/<str:agent_id>/', call_play_ai_api, name='get_agent'),
    path('fetch-recording/t/<path:recording_url>/', fetch_twilio_recording, name='fetch-recording'),
    path('agent/', create_or_update_agent, name='create_agent'),  # For creating new agents
    path('agent/<int:id>/', create_or_update_agent, name='update_agent'),  # For updating existing agents
    path('delete-agent/<int:id>/', delete_agent, name='delete_agent'),
    path('get-conversation/<str:agent_id>/', get_conversation, name='get_conversation'),
    path('get-transcript/<str:agent_id>/<str:cid>/', get_transcript, name='get_transcript'),
    path('dashboards/', dashboards, name='dashboards'),
    path('api/dashboard-stats/', dashboard_stats_api, name='dashboard-stats-api'),
    path('login/', login, name='login'),
    path('signup/', signup, name='signup'),
    path('reset-password/', reset, name='reset'),
    path('logout/', logout_user, name='logout'), 
    path('play-ai-service/', service_detail_view, name='play_ai_service'),
    path('twilio-service/', twilio_service_detail_view, name='twilio_service'),
    path('summarize_transcript/<str:agent_id>/<str:cid>/', summarize_transcript, name='summarize_transcript'),
    path('call_history/', call_history, name='call_history'),
    path('call-history/data/', call_history_data, name='call_history_data'),
    path('call_history/<int:id>/', call_detail, name='call_detail'),
    path('analyze-call-summary/', analyze_call_summary, name='analyze_call_summary'),
    path('agent/setup/', agent_setup, name='agent_setup'),
    path('onboard/', onboard, name='onboard'),
    path('api/playai/webhook/', playai_webhook, name='playai-webhook'),
    path('create-agent/', AgentCreateView.as_view(), name='create-agent'),
    path('add-twilio-phone/', add_twilio_phone, name='add_twilio_phone'),
    path('api/twilio-phones/list/',list_twilio_phones, name='list_twilio_phones'),
    path("api/twilio-phones/update/<int:pk>/", update_twilio_phone, name="update_twilio_phone"),
    path("api/twilio-phones/delete/<int:pk>/", delete_twilio_phone, name="delete_twilio_phone"),


    

]
