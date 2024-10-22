from django.urls import path
from .views import upload_file,call_initate,voice
app_name = 'callapp'
urlpatterns = [
    path('upload/', upload_file, name='upload_file'),
    path('call/<str:agent_id>/', call_initate, name='call'),
    path('voice/<str:agent_id>/', voice, name='voice')
]
