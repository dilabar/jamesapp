import json
from time import localtime
from django.http import HttpResponse, JsonResponse
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.models import User

from django.contrib.auth import login as auth_login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from contact.models import List
from logger.models import ActivityLog
import openai
from agent.forms import ServiceDetailForm,AgentForm
from agent.models import Agent, ServiceDetail
from jamesapp.utils import decrypt, get_conversation_data, get_transcript_data


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

@login_required
def dashboard_stats_api(request):
    try:
        total_agents_active = Agent.objects.filter(user=request.user).count()
        total_campaigns = Campaign.objects.filter(user=request.user).count()
        total_lists = List.objects.filter(user=request.user).count()
        total_contacts = Contact.objects.filter(user=request.user).count()
        total_phonecalls = PhoneCall.objects.filter(user=request.user).count()
        # Recent Activity Logs
        logs = ActivityLog.objects.filter(user=request.user).order_by('-timestamp')[:10]  # latest 10 logs
        
        logs_data = []
        for log in logs:
            logs_data.append({
                'user': log.user.get_full_name() or log.user.username,
                'timestamp': log.timestamp,
                'action': log.action,
                'additional_info': log.additional_info,
                'img_url': '/static/manish/images/user/26.png'  # You can customize per user later
            })
        data = {
            'total_agents_active': total_agents_active,
            'total_campaigns': total_campaigns,
            'total_lists': total_lists,
            'total_contacts': total_contacts,
            'total_phonecalls': total_phonecalls,
            'activity_logs': logs_data
        }

        return JsonResponse(data, status=200)

    except Exception as e:
        # Log the error here if needed
        print(e)
        return JsonResponse(
            {'error': 'Something went wrong while fetching dashboard stats.'},
            status=500
        )




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




def reset(request):
    
    return render(request, 'auth/forgot_password.html')
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


@login_required
def add_twilio_phone(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone = data.get('phone_number')
            service_id = data.get('service_id')

            # Validate phone number
            if not phone or len(phone) < 10:
                return JsonResponse({'success': False, 'error': 'Invalid phone number.'})

            # Validate service ID
            if not service_id:
                return JsonResponse({'success': False, 'error': 'Service ID is required.'})

            # Fetch service associated with the user
            service = ServiceDetail.objects.get(id=service_id, user=request.user)

            # Create the Twilio phone number entry
            twilio_phone = TwilioPhoneNumber.objects.create(service=service, phone_number=phone)

            return JsonResponse({'success': True, 'phone_number': twilio_phone.phone_number})
        except ServiceDetail.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Service ID not found for the user.'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
def list_twilio_phones(request):
    try:
        service_id = request.GET.get("service_id")
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))
        search_value = request.GET.get("search[value]", "")

        if not service_id:
            return JsonResponse({"error": "Missing service_id"}, status=400)

        queryset = TwilioPhoneNumber.objects.filter(service_id=service_id)

        if search_value:
            queryset = queryset.filter(phone_number__icontains=search_value)

        total_records = TwilioPhoneNumber.objects.filter(service_id=service_id).count()
        filtered_records = queryset.count()

        page_data = queryset[start:start + length]

        data = [
            [start + i + 1, phone.phone_number, phone.id]
            for i, phone in enumerate(page_data)
        ]

        return JsonResponse({
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": filtered_records,
            "data": [
                [row[0], row[1], f'''
                    <button class="btn btn-sm btn-warning edit-phone" data-id="{row[2]}" data-phone="{row[1]}">Edit</button>
                    <button class="btn btn-sm btn-danger delete-phone" data-id="{row[2]}">Delete</button>
                '''] for row in data
            ],
        })

    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

@login_required
def update_twilio_phone(request, pk):
    try:
        phone = TwilioPhoneNumber.objects.select_related('service').get(pk=pk)

        # Check ownership
        if phone.service.user != request.user:
            return JsonResponse({"success": False, "error": "Permission denied."}, status=403)

        data = json.loads(request.body)
        new_phone_number = data.get("phone_number")

        # Validate the new phone number
        if not new_phone_number or len(new_phone_number) < 10:
            return JsonResponse({"success": False, "error": "Invalid phone number."})

        phone.phone_number = new_phone_number
        phone.save()

        return JsonResponse({"success": True})
    except TwilioPhoneNumber.DoesNotExist:
        return JsonResponse({"success": False, "error": "Phone number not found."})
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON data."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
def delete_twilio_phone(request, pk):
    try:
        phone = TwilioPhoneNumber.objects.select_related('service').get(pk=pk)

        # Check ownership
        if phone.service.user != request.user:
            return JsonResponse({"success": False, "error": "Permission denied."}, status=403)

        phone.delete()
        return JsonResponse({"success": True})
    except TwilioPhoneNumber.DoesNotExist:
        return JsonResponse({"success": False, "error": "Phone number not found."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
