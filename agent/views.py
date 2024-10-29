import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.models import User

from django.contrib.auth import login as auth_login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

from agent.models import Agent


def call_play_ai_api(request, agent_id):
    url = f"https://api.play.ai/api/v1/agents/{agent_id}"

    headers = {
        "Authorization": f"Bearer {settings.PLAY_AI_API_KEY}",
        "X-USER-ID": settings.PLAY_AI_USER_ID,
        "Accept": "application/json"
    }

    try:
        # Make the GET request
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the API response as JSON
        agent_data = response.json()

        # Render the agent details in an HTML template
        return render(request, 'agent/agent_detail.html', {'agent': agent_data})

    except requests.exceptions.RequestException as e:
        return render(request, 'error.html', {'error': str(e)})
    
def agent_list(request):
    agents = Agent.objects.all()  # Fetch all agents from the database
    context={
        'agents': agents
    }
    return render(request, 'agent/agent_list.html', context)


def dashboards(request):
    
    return render(request, 'crm/dash.html')






# Signup View
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Check if the username or email is already taken
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
        elif password1 != password2:
            messages.error(request, "Passwords do not match.")
        else:
            try:
                user = User.objects.create_user(username=username, email=email, password=password1)
                user.save()
                auth_login(request, user)  # Automatically log in the user after signup
                messages.success(request, "Registration successful! Welcome!")
                return redirect('login')  # Redirect to a home or success page after signup
            except Exception as e:
                messages.error(request, f"Error occurred: {e}")

    return render(request, 'crm/signup.html')


# Login View
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('dashboards')  # Redirect to the home page or dashboard after login
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'crm/login.html')



def logout(request):
    logout(request)  
    return redirect('login') 




def reset(request):
    
    return render(request, 'crm/resetpassword.html')