from django.urls import path
from . import views
app_name="agency"
urlpatterns = [
    path('create_subaccount/', views.add_subaccount, name='create_subaccount'),
    # path('subaccount/<int:subaccount_id>/configure/', views.configure_subaccount, name='configure_subaccount'),
    path('subaccounts/', views.subaccount_list, name='list_subaccounts'),
    path('switch_account/<int:subaccount_id>/', views.switch_account, name='switch_account'),
    # path('register/', agency_register, name='agency_register'),
    # path('subaccounts/add/', add_subaccount, name='add_subaccount'),
    # path('subaccounts/', subaccount_list, name='subaccount_list'),
]
