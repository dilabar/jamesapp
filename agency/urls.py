from django.urls import path
from . import views
app_name="agency"
urlpatterns = [
    path('create_subaccount/', views.create_subaccount, name='create_subaccount'),
    path('subaccount/<int:subaccount_id>/configure/', views.configure_subaccount, name='configure_subaccount'),
    path('subaccounts/', views.list_subaccounts, name='list_subaccounts'),
]
