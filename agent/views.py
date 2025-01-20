from django.http import HttpResponse
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.models import User

from django.contrib.auth import login as auth_login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
import openai
from agent.forms import ServiceDetailForm,AgentForm
from agent.models import Agent, ServiceDetail
from jamesapp.utils import decrypt, get_conversation_data, get_transcript_data
from django.http import JsonResponse

from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password

import json
from random import randint
from .forms import *



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
@login_required
def agent_list(request):
    # Check if the logged-in user is an agency
    if request.user.is_agency():
        # Show agents for the agency and all its sub-accounts
        agents = Agent.objects.filter(user=request.user)
    else:
        # Show only the logged-in user's agents
        agents = Agent.objects.filter(user=request.user.parent_agency)
        
    
    context = {
        'agents': agents
    }
    return render(request, 'new/my_agent_list.html', context)

@login_required
def dashboards(request):
    
    return render(request, 'dashboard/dashboard.html')






# Signup View
def signup(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()  # Save the user and create the agency account
                auth_login(request, user)  # Automatically log in the user after signup
                messages.success(request, 'Your agency account has been created successfully. You can now log in.')
                return redirect('agent:login')  # Redirect to a home or login page after signup
            except Exception as e:
                print(f"Error occurred: {e}")
                messages.error(request, f"Error occurred: {e}")
        else:
            # If the form is not valid, show errors
            print(form.errors)
            messages.error(request, "There was an error with the registration form.")
    else:
        form = RegisterForm()
    
    return render(request, 'auth/register.html', {'form': form})


# Login View
def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('agent:dashboards')  # Redirect to the home page or dashboard after login
        else:
            messages.error(request, "Invalid username or password.")
    
    return render(request, 'auth/login.html')



def logout_user(request):
    logout(request)  
    return redirect('agent:login') 





@login_required
def service_detail_view(request):
    # Get the user's existing service details for Twilio and Play.ai
    if not request.user.is_authenticated:
        return redirect('agent:login') 
    user = request.user
    play_ai_service = ServiceDetail.objects.filter(user=user, service_name='play_ai').first()
    if request.method == 'POST':
        # Create separate forms for each service
        play_ai_form = ServiceDetailForm(request.POST, instance=play_ai_service)

        if play_ai_form.is_valid():
            play_ai_form.save(user=user)
            play_ai_form.save()
            messages.success(request, 'Service details saved successfully!')
            return redirect('agent:play_ai_service')  # Redirect to a success page or dashboard
        else:
            messages.error(request, 'There were errors in the form. Please correct them.')

    else:
        # Initialize forms for existing services
        play_ai_form = ServiceDetailForm(instance=play_ai_service)

    return render(request, 'service/play-ai-create-form.html', {
        'play_ai_form': play_ai_form,
    })
@login_required
def twilio_service_detail_view(request):
    # Get the user's existing service details for Twilio and Play.ai
    if not request.user.is_authenticated:
        return redirect('agent:login') 
    user = request.user
    twilio = ServiceDetail.objects.filter(user=user, service_name='twilio').first()
    if request.method == 'POST':
        # Create separate forms for each service
        twilio_form = ServiceDetailForm(request.POST, instance=twilio)

        if twilio_form.is_valid():
            twilio_form.save(user=user)
            twilio_form.save()
            messages.success(request, 'Service details saved successfully!')
            return redirect('agent:twilio_service')  # Redirect to a success page or dashboard
        else:
            messages.error(request, 'There were errors in the form. Please correct them.')

    else:
        # Initialize forms for existing services
        twilio_form = ServiceDetailForm(instance=twilio)

    return render(request, 'service/twilio-create-form.html', {
        'twilio_form': twilio_form,
    })

@login_required
def create_or_update_agent(request, id=None):
    # If agent_id is provided, try to fetch the agent for editing
    if not request.user.is_authenticated or not request.user.is_agency:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('home')  # Redirect to a relevant page

    if id is not None:
        agent = Agent.objects.filter(id=id, user=request.user).first()
    else:
        agent = None  # No existing agent, creating a new one

    if request.method == 'POST':
        form = AgentForm(request.POST, instance=agent)
        if form.is_valid():
            # Save the agent, associating it with the current user
            new_agent = form.save(commit=False)
            new_agent.user = request.user
            new_agent.save()
            
            messages.success(request, f"Agent {'updated' if agent else 'created'} successfully!")
            return redirect('agent:agent_list')  # Redirect to a list view or detail page as needed
    else:
        form = AgentForm(instance=agent)
    
    return render(request, 'new/onboard.html', {'form': form, 'agent': agent})
@login_required
def delete_agent(request, id):
    # dec_agent_id=decrypt(agent_id)
    agent = get_object_or_404(Agent, id=id)
    if request.method == "POST":
        agent.delete()
        messages.success(request, "Agent deleted successfully.")
    return redirect('agent:agent_list')
@login_required
def get_conversation(request, agent_id):
    play_ai = ServiceDetail.objects.filter(user=request.user, service_name='play_ai').first()
    ag=decrypt(agent_id)
    data = get_conversation_data(ag,play_ai.decrypted_api_key,play_ai.decrypted_account_sid)
    if isinstance(data, dict) and "error" in data:
        # Handle error scenario
        context = {"error": data["error"]}
    else:
        # Assume data is a list of results
        context = {"data_list": data,"agent_id":agent_id}
    return render(request, 'new/all_conversation.html', context)

@login_required
def get_transcript(request, agent_id,cid):
    play_ai = ServiceDetail.objects.filter(user=request.user, service_name='play_ai').first()
    ag=decrypt(agent_id)
    data = get_transcript_data(ag,cid,play_ai.decrypted_api_key,play_ai.decrypted_account_sid)
    if isinstance(data, dict) and "error" in data:
        # Handle error scenario
        context = {"error": data["error"]}
    else:
        # Assume data is a list of results
        context = {"data_list": data}
    return render(request, 'agent/transcript.html', context)




@login_required
def summarize_transcript(request, agent_id, cid):
    try:
        openai.api_key=settings.OPEN_AI_API_KEY
        play_ai = ServiceDetail.objects.filter(user=request.user, service_name='play_ai').first()
        ag=decrypt(agent_id)
        # Call the function to get the transcript data (returns JSON)
        transcript_list = get_transcript_data(ag, cid, play_ai.decrypted_api_key, play_ai.decrypted_account_sid)

        # Extract the transcript content from the JSON response
        combined_transcript = "\n\n".join([transcript.get('content', '') for transcript in transcript_list]) # Assuming the JSON has a key 'content' for the transcript
        if not combined_transcript:
            return render(request, 'agent/error.html', {'error_message': 'No transcript content available.'})

        # Call the OpenAI API to summarize the transcript
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Updated model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Summarize the following transcript:\n\n{combined_transcript}"}
            ],
            max_tokens=150,  # Set the maximum token limit for the summary
            temperature=0.5,  # Controls the randomness of the response (lower value = more focused)
        )
        # print("OpenAI Response:", response)
        # Get the summary from the response
        summary = response['choices'][0]['message']['content'].strip()

        # Return the summary and the original transcript to the template
        context = {
            'summary': summary,
            'combined_transcript': combined_transcript,
        }
        return render(request, 'agent/transcript_summary.html', context)

    except Exception as e:
        return render(request, 'agent/error.html', {'error': f"Error during summarization: {str(e)}"})




def password_reset(request):
    return render(request, 'auth/forgot_password.html')



def send_otp(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            flag = data.get('flag', False)

            if not email:
                return JsonResponse({'success': False, 'message': 'Email is required.'})

            # Case-insensitive email search
            user = User.objects.filter(email__iexact=email).first()
            
            if not flag and not user:
                return JsonResponse({'success': False, 'message': 'No user found with this email.'})

            otp = randint(100000, 999999)  # Generate a random 6-digit OTP

            # Save OTP and email in the session
            request.session['reset_email'] = email
            request.session['otp'] = otp

            # Send OTP via email
            send_mail(
                'Password Reset OTP',
                f'Your OTP for password reset is: {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )

            return JsonResponse({'success': True, 'message': 'OTP sent to your email.'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON format.'})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})

# Verify the OTP entered by the user
def verify_otp(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            otp = data.get('otp')

            if not otp:
                return JsonResponse({'success': False, 'message': 'OTP is required.'})

            # Check OTP against session value
            session_otp = request.session.get('otp')
            if session_otp and int(otp) == session_otp:
                request.session['otp_verified'] = True
                return JsonResponse({'success': True, 'message': 'OTP verified successfully.'})
            else:
                return JsonResponse({'success': False, 'message': 'Invalid OTP.'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON format.'})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def reset_password(request):
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            new_password = data.get('new_password')

            if not new_password:
                return JsonResponse({'success': False, 'message': 'Password is required.'})

            # Ensure OTP was verified before allowing password reset
            if request.session.get('otp_verified'):
                email = request.session.get('reset_email')
                try:
                    user = User.objects.get(email=email)
                    user.password = make_password(new_password)
                    user.save()

                    # Clear session data
                    request.session.pop('reset_email', None)
                    request.session.pop('otp', None)
                    request.session.pop('otp_verified', None)

                    return JsonResponse({'success': True, 'message': 'Password reset successfully.'})
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'User does not exist.'})
            else:
                return JsonResponse({'success': False, 'message': 'OTP verification required.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'An error occurred: ' + str(e)})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})