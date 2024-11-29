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