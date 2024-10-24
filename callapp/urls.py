from django.urls import path
from .views import call_initate,voice
app_name = 'callapp'
urlpatterns = [
    path('call/<str:agent_id>/', call_initate, name='call'),
    path('voice/<str:agent_id>/', voice, name='voice')
]
