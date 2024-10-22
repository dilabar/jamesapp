from django.urls import path
from .views import *

urlpatterns = [
    path('upload/', upload_file, name='upload_file'),
    path('agents/', agents, name='agents'),
    path('agentsdetails/', agentsdetails, name='agentsdetails'),
]
