from django.urls import path
from .views import *
from .api_view import BulkActionTriggerView, BulkActionStatusView, NoteAPI

app_name='contact'
urlpatterns = [
    path('', contact_list, name='contact_list'),
    path('data/', contact_data, name='contact_data'),  # 🔥 New API endpoint
    path('select-contacts/',select_contacts,name='select_contacts'),
    path('select-lists/',select_lists,name='select_lists'),

    path('details/<int:id>/', contact_details, name='contact_details'),
    path('delete/<int:id>/', delete_contact, name='delete_contact'),
    path('add/', add_contact, name='add_contact'),
    path('upload/', upload_excel, name='upload_excel'),
    path('extract/', extract_file, name='extract_file'),
    path('create-bulk/', create_bulk_contacts, name='create_bulk'),
    path('lists/', list_overview, name='list_overview'),
    path('list-data/', list_data, name='list_data'),
    path('lists/create/', create_list, name='create_list'),
    path('lists/<int:list_id>/', list_detail, name='list_detail'),
    path('list/<int:list_id>/data/', list_detail_data, name='list_detail_data'),
    path('list/edit/<int:list_id>/', edit_list, name='edit_list'),

    path('lists/delete/<int:list_id>/', delete_list, name='delete_list'),
    # path('campaigns/create/', create_campaign, name='create_campaign'),
    path('campaigns/<int:campaign_id>/', campaign_detail_v1, name='campaign_detail'),
    path('campaign/<int:campaign_id>/pause/', revoke_campaign_task, name='revoke_campaign_task'),
    path('campaign/<int:campaign_id>/restart/', restart_campaign_task, name='restart_campaign_task'),
    
    path('campaigns/delete/<int:campaign_id>/', delete_campaign, name='delete_campaign'),
    path('create-list/', create_list, name='create_list'),
    path('create-campaign/', create_campaign, name='create_campaign'),
    path('campaigns/', campaign_list, name='campaign_list'),
    path('campaigns/data/', campaign_data, name='campaign_data'),
    path('start_campaign/<int:campaign_id>/', start_campaign, name='start_campaign'),
    path('custom-fields/add/', add_custom_field, name='add_custom_field'),
    path('bulk_upload/',bulk_upload,name='bulk_upload'),
    path('bulk_action_list/',bulk_action_list,name='bulk_action_list'),


    path('custom-fields/', custom_fields, name='custom_fields'),
    path('campaign/<int:campaign_id>/edit/', edit_campaign, name='edit_campaign'),
    path('delete_custom_field/<int:field_id>/', delete_custom_field, name='delete_custom_field'),

     # Trigger the bulk action (POST)
    path('api/bulk-action/', BulkActionTriggerView.as_view(), name='bulk_action_trigger'),

    # Check the status of a bulk action (GET)
    path('api/bulk-action/<int:action_id>/status/', BulkActionStatusView.as_view(), name='bulk_action_status'),
    path('api/notes/<int:contact_id>/', NoteAPI.as_view(), name='notes_api'),
    path('api/notes/<int:contact_id>/<int:note_id>/', NoteAPI.as_view(), name='note_detail_api'),
    path("api/start-campaign/<int:campaign_id>/", start_campaign_view, name="start_campaign_api"),
]