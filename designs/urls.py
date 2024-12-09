from django.urls import path
from .views import *
app_name = 'designs'
urlpatterns = [
    path('', login_user, name='login_user'),
    path('register/', register, name='register'),
    path('lock/', lock, name='lock'),
    path('forgot-password/', forgot_password, name='register'),
    path('maintainance/', maintainance, name='maintainance'),

    path('dashboard/', dashboard, name='dashboard'),

    #
]
