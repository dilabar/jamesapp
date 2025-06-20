from django.urls import path
from .views import *
app_name = 'callapp'
urlpatterns = [
    
    path('start-calling/', start_calling, name='start_calling'),
    path('agent-card/', start_card, name='start_card'),
    path('start-calling/<int:agnt_id>/', call_initiate, name='call'),
    path('start_twilio_voice/<int:user_id>/<int:agnt_id>/', twilio_voice, name='twilio_voice'),
    path('start_twilio_stream/<int:user_id>/<int:agnt_id>/<int:camp_id>/', start_twilio_stream, name='start_twilio_stream'),
    path('twilio/get_call_log/', getcall_log, name='getcall_log'),
    path('twilio/get_twilio_call_recordings/<str:call_sid>/', get_twilio_call_recordings, name='get_twilio_call_recordings'),
    path("transfer_call/<str:phone_number>/<str:cal_sid>/", transfer_call, name="transfer_call"),
    path("forward_call/play_ai/", forward_call, name="forward_call"),
    path('handle_dtmf_input/<str:cal_sid>/', handle_dtmf_input, name='handle_dtmf_input'),
    path('join_conference/1/', join_conference, name='join_conference'),
    path('conference_dtmf_url/<str:cal_sid>/', conference_dtmf_url, name='conference_dtmf_url'),
    path('call_status_callback/<int:id>/', call_status_callback, name='call_status_callback'),
    path('transcription_callback/<int:id>/', transcription_callback, name='transcription_callback'),

]
