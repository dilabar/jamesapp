from django.urls import path
from .views import *

app_name='contact'
urlpatterns = [
    path('', contact_list, name='contact_list'),
    path('details/<int:id>/', contact_details, name='contact_details'),
    path('add/', add_contact, name='add_contact'),
    path('upload/', upload_excel, name='upload_excel'),
    path('extract/', extract_file, name='extract_file'),
    path('create-bulk/', create_bulk_contacts, name='create_bulk'),
    path('jobs/', list_jobs, name='list_jobs'),
    path('jobcontrol/', control_job, name='control_job'),
    path('lists/', list_overview, name='list_overview'),
    path('lists/create/', create_list, name='create_list'),
    path('create-bulk-list/', create_bulk_contact_list, name='create_bulk_contact_list'),
    path('lists/<int:list_id>/', list_detail, name='list_detail'),
    path('campaigns/create/', create_campaign, name='create_campaign'),
    path('campaigns/<int:campaign_id>/', campaign_detail, name='campaign_detail'),
    path('create-list/', create_list, name='create_list'),
    path('create-campaign/', create_campaign, name='create_campaign'),
    path('campaigns/', campaign_list, name='campaign_list'),
    path('start_campaign/<int:campaign_id>/', start_campaign, name='start_campaign'),
   
]