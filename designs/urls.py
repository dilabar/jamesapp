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

    #agents
    path('agent-onboarding/', onboard, name='onboard'),
    path('agent-list/', agent_list, name='agent_list'),
    path('agent-card/', start_card, name='start_card'),
    path('start-calling/', start_calling, name='start_calling'),
    path('all-conversation/', all_conversation, name='all_conversation'),
    path('all-conversation-detail/', all_conversation_detail, name='all_conversation_detail'),
    path('all-conversation-log/', all_conversation_log, name='all_conversation_log'),
    
    path('agent-card-2/', start_card2, name='start_card2'),

]
