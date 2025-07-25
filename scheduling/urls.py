from django.urls import path
from .views import *

app_name='scheduling'
urlpatterns = [
    path('', integrations_view, name='integrations_view'),
    path('oauth/', google_oauth, name='google_oauth'),
    path('oauth/callback/', google_oauth_callback, name='google_oauth_callback'),
    path('event-list/' , event_list , name='event_list'),
    path('events/data/', event_list_data, name='event_list_data'),
]