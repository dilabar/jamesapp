from django.urls import path
from .views import *
from .api_view import BulkActionTriggerView, BulkActionStatusView, NoteAPI

app_name='contact'
urlpatterns = [
    path('', contact_list, name='contact_list'),
    path('details/<int:id>/', contact_details, name='contact_details'),
    path('add/', add_contact, name='add_contact'),
    path('upload/', upload_excel, name='upload_excel'),
    path('extract/', extract_file, name='extract_file'),
    path('create-bulk/', create_bulk_contacts, name='create_bulk'),
    path('lists/', list_overview, name='list_overview'),
    path('lists/create/', create_list, name='create_list'),
    path('lists/<int:list_id>/', list_detail, name='list_detail'),
    # path('campaigns/create/', create_campaign, name='create_campaign'),
    path('campaigns/<int:campaign_id>/', campaign_detail, name='campaign_detail'),
    path('create-list/', create_list, name='create_list'),
    path('create-campaign/', create_campaign, name='create_campaign'),
    path('campaigns/', campaign_list, name='campaign_list'),
    path('start_campaign/<int:campaign_id>/', start_campaign, name='start_campaign'),
    path('custom-fields/add/', add_custom_field, name='add_custom_field'),
    path('bulk_upload/',bulk_upload,name='bulk_upload'),
    path('bulk_action_list/',bulk_action_list,name='bulk_action_list'),

     # Trigger the bulk action (POST)
    path('api/bulk-action/', BulkActionTriggerView.as_view(), name='bulk_action_trigger'),

    # Check the status of a bulk action (GET)
    path('api/bulk-action/<int:action_id>/status/', BulkActionStatusView.as_view(), name='bulk_action_status'),
    path('api/notes/<int:contact_id>/', NoteAPI.as_view(), name='notes_api'),
    path('api/notes/<int:contact_id>/<int:note_id>/', NoteAPI.as_view(), name='note_detail_api'),
]