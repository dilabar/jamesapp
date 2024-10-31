from django.urls import path
from .views import call_initiate,start_twilio_stream
app_name = 'callapp'
urlpatterns = [
    path('<str:agent_id>/', call_initiate, name='call'),
    path('start_twilio_stream/<str:agent_id>/', start_twilio_stream, name='start_twilio_stream')
]
