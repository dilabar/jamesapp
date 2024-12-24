from django.urls import path
from . import views

urlpatterns = [
    path('create_subaccount/', views.create_subaccount, name='create_subaccount'),
    path('subaccount/<int:subaccount_id>/configure/', views.configure_subaccount, name='configure_subaccount'),
]
