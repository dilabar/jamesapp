from django.urls import path
from . import views

urlpatterns = [
    path('view_bill/', views.view_bill, name='view_bill'),
    path('create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
    path('payment-success/', views.payment_success, name='payment-success'),
    path('payment-cancel/', views.payment_cancel, name='payment-cancel'),
]