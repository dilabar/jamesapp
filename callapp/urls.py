from django.urls import path
from .views import call_initiate,start_twilio_stream,getcall_log,get_twilio_call_recordings,transfer_call
app_name = 'callapp'
urlpatterns = [
    path('<str:agent_id>/', call_initiate, name='call'),
    path('start_twilio_stream/<int:user_id>/<str:agent_id>/', start_twilio_stream, name='start_twilio_stream'),
    path('twilio/get_call_log/', getcall_log, name='getcall_log'),
    path('twilio/get_twilio_call_recordings/<str:call_sid>/', get_twilio_call_recordings, name='get_twilio_call_recordings'),
    path("transfer_call/<str:phone_number>/", transfer_call, name="transfer_call"),

]
