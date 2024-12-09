from django.shortcuts import render, redirect

# Create your views here.
def login_user(request):
    return render(request, 'auth/login.html')

def register(request):
    return render(request, 'auth/register.html')


def lock(request):
    return render(request, 'auth/locked.html')


def forgot_password(request):
    return render(request, 'auth/forgot_password.html')


def maintainance(request):
    return render(request, 'auth/maintain.html')

def dashboard(request):
    return render(request, 'dashboard/dashboard.html')

def onboard(request):
    return render(request, 'agent/onboard.html')

def agent_list(request):
    return render(request, 'agent/my_agent_list.html')

def start_card(request):
    return render(request, 'agent/agent_card.html')

def start_card2(request):
    return render(request, 'agent/agent_card2.html')

def start_calling(request):
    return render(request, 'agent/start_calling.html')

def all_conversation(request):
    return render(request, 'agent/all_conversation.html')

def all_conversation_detail(request):
    return render(request, 'agent/all_conversation_detail.html')