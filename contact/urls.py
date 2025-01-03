from django.urls import path
from .views import *

app_name='contact'
urlpatterns = [
    path('', contact_list, name='contact_list'),
    path('add/', add_contact, name='add_contact'),
    path('upload/', upload_excel, name='upload_excel'),
    path('lists/', list_overview, name='list_overview'),
    path('lists/create/', create_list, name='create_list'),
    path('lists/<int:list_id>/', list_detail, name='list_detail'),
    path('campaigns/create/', create_campaign, name='create_campaign'),
    path('campaigns/<int:campaign_id>/', campaign_detail, name='campaign_detail'),
    path('create-list/', create_list, name='create_list'),
    path('create-campaign/', create_campaign, name='create_campaign'),
]