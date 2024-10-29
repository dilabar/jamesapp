from django.urls import path
from .views import *

urlpatterns = [
    path('', agent_list, name='agent_list'),
    path('get-agent/<str:agent_id>/', call_play_ai_api, name='get_agent'),
    path('dashboards/', dashboards, name='dashboards'),
    path('login/', login, name='login'),
    path('signup/', signup, name='signup'),
    path('reset-password/', reset, name='reset'),
    path('logout/', logout, name='logout'), 
]
