from django.shortcuts import render, redirect ,  get_object_or_404
from django.core.paginator import Paginator
from django.views.generic import ListView
from requests import request
from agent.forms import *
import openpyxl
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from twilio.rest import Client
from django.http import JsonResponse
import json
from django.utils import timezone

from contact.forms import CampaignForm, ContactForm, EmailForm, ExcelUploadForm, PhoneNumberForm
from contact.models import *



def contact_list(request):
    if request.user.is_agency():

        contacts = Contact.objects.filter(user__in=request.user.get_all_subaccounts())
    else:
        contacts = Contact.objects.filter(user=request.user)

    
    # Pagination setup
    paginator = Paginator(contacts, 10)  # Show 10 contacts per page
    page_number = request.GET.get('page')  # Get the current page number
    page_obj = paginator.get_page(page_number)  # Get the contacts for the current page
    
    # Prepare context
    context = {
        'page_obj': page_obj,
        'contacts': contacts,  # You can also pass the full list if needed elsewhere
        'page_range': paginator.page_range,  # The range of page numbers
        'page_number': page_obj.number,  # Current page number
    }
    
    return render(request, 'new/contact_list.html', context)





@login_required
def add_contact(request):
    """Handles creating a new contact with associated email, phone, lists, and campaigns."""
    all_lists = List.objects.filter(user=request.user)  # Filter lists by logged-in user
    all_campaigns = Campaign.objects.filter(lists__user=request.user).distinct()  # Filter campaigns by user's lists

    if request.method == 'POST':
        
        try:
            # Parse JSON data
            data = json.loads(request.body)

            # Process `contact_info` or save to database
            first_name = data.get('firstName', '')
            last_name = data.get('lastName', '')
            emails = data.get('emails', {})
            phone_data = data.get('phoneData', {})
            contact_type = data.get('contactType', '')
            time_zone = data.get('timeZone', '')

            contact = Contact.objects.create(user=request.user,first_name=first_name,last_name=last_name,email=emails,phone=phone_data,contact_type=contact_type,time_zone=time_zone,created_at=timezone.now())
            contact.save()

            # Example response
            return JsonResponse({'status': 'success', 'message': 'Contact added successfully!'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid HTTP method'}, status=405)
    #     contact_form = ContactForm(request.POST, request.FILES)  # Include files for handling uploaded photos
    #     email_form = EmailForm(request.POST)
    #     phone_form = PhoneNumberForm(request.POST)
    #     selected_lists = request.POST.getlist('lists')
    #     selected_campaigns = request.POST.getlist('campaigns')

    #     if contact_form.is_valid() and email_form.is_valid() and phone_form.is_valid():
    #         # Save the contact
    #         contact = contact_form.save(commit=False)
    #         contact.user = request.user  # Assign the logged-in user
    #         contact.save()

    #         # Save the associated email
    #         email = email_form.save(commit=False)
    #         email.contact = contact
    #         email.user = request.user  # Assign the logged-in user
    #         email.save()

    #         # Handle phone number uniqueness
    #         phone_number = phone_form.save(commit=False)
    #         phone_number.contact = contact
    #         phone_number.user = request.user  # Assign the logged-in user

    #         try:
    #             # Check if this phone number already exists for the user
    #             existing_phone_number = PhoneNumber.objects.filter(user=request.user, phone_number=phone_number.phone_number).first()
    #             if existing_phone_number:
    #                 # If it exists, display an error message
    #                 messages.error(request, f"The phone number {phone_number.phone_number} is already associated with your account.")
    #                 return redirect('contact:add_contact')

    #             # If the phone number is unique, save it
    #             phone_number.save()

    #         except IntegrityError:
    #             # Handle IntegrityError if any happens (to be extra cautious)
    #             messages.error(request, "There was an error saving the phone number. Please try again.")
    #             return redirect('contact:add_contact')

    #         # Associate contact with selected lists
    #         for list_id in selected_lists:
    #             list_obj = get_object_or_404(List, id=list_id, user=request.user)
    #             list_obj.contacts.add(contact)

    #         # Associate contact with selected campaigns
    #         for campaign_id in selected_campaigns:
    #             campaign_obj = get_object_or_404(Campaign, id=campaign_id, lists__user=request.user)
    #             campaign_obj.individual_contacts.add(contact)

    #         return redirect('contact:contact_list')  # Redirect to the contact list page
    # else:
    #     contact_form = ContactForm()
    #     email_form = EmailForm()
    #     phone_form = PhoneNumberForm()

    # return render(request, 'new/add_contact.html', {
    #     'contact_form': contact_form,
    #     'email_form': email_form,
    #     'phone_form': phone_form,
    #     'all_lists': all_lists,
    #     'all_campaigns': all_campaigns,
    # })




def upload_excel(request):
    if request.method == 'POST' and request.FILES['excel_file']:
        excel_file = request.FILES['excel_file']
        
        # Open the Excel file
        workbook = openpyxl.load_workbook(excel_file)
        sheet = workbook.active
        
        # Iterate through rows in the Excel file
        for row in sheet.iter_rows(min_row=2, values_only=True):  # Start from row 2 (skip headers)
            first_name = row[0]  # Assuming first name is in column A
            last_name = row[1]   # Assuming last name is in column B
            email = row[2]       # Assuming email is in column C
            phone = row[3]       # Assuming phone number is in column D
            contact_type = row[4]  # Assuming contact type is in column E
            time_zone = row[5]     # Assuming time zone is in column F
            
            # Create a new contact
            contact = Contact.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                contact_type=contact_type,
                time_zone=time_zone
            )
            
            # Add email if present
            if email:
                Email.objects.create(contact=contact, email=email)
            
            # Add phone if present
            if phone:
                PhoneNumber.objects.create(contact=contact, phone=phone)

        messages.success(request, 'Excel file uploaded and contacts created successfully!')
        return redirect('agent:contact_list')  # Redirect to the contact list page after successful upload

    return render(request, 'new/upload_contact.html', {'form': ExcelUploadForm()})






def create_list(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        contact_ids = request.POST.getlist('contacts')
        contacts = Contact.objects.filter(id__in=contact_ids)

        try:
            # Attempt to create the list
            new_list = List.objects.create(name=name, description=description,user=request.user)
            new_list.contacts.set(contacts)  # Associate selected contacts
            return redirect('contact:contact_list')  # Redirect after successful creation
        except IntegrityError:
            # Handle duplicate name error
            error_message = "A list with this name already exists. Please choose a different name."
            return render(request, 'new/create_list.html', {
                'error_message': error_message,
                'contacts': Contact.objects.all(),  # Pass contacts for the form
            })
    else:
        return render(request, 'new/create_list.html', {
            'contacts': Contact.objects.filter(user__in=request.user.get_all_subaccounts()),  # Pass contacts for the form
        })


def list_overview(request):
    if request.user.is_agency():

        listsd = List.objects.filter(user__in=request.user.get_all_subaccounts())
        print(request.user.get_all_subaccounts())
    else:
        listsd = List.objects.filter(user=request.user)

    context = {'lists': listsd}
    return render(request, 'new/list_overview.html', context)

def list_detail(request, list_id):
    list_obj = get_object_or_404(List, id=list_id)
    return render(request, 'new/list_detail.html', {'list': list_obj})



@login_required
def create_campaign(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST, user=request.user)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.user = request.user  # Assign logged-in user
            campaign.save()
            form.save_m2m()  # Save Many-to-Many relationships
            return redirect('contact:campaign_detail', campaign_id=campaign.id)
    else:
        form = CampaignForm(user=request.user)

    return render(request, 'new/create_campaign.html', {'form': form})



def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    agdetail=Agent.objects.filter(user=request.user.parent_agency)
    context={
        'campaign': campaign,
        'agdetail':agdetail

    }
    return render(request, 'new/campaign_detail.html', context)
@login_required
def campaign_list(request):
    # Fetch campaigns for the logged-in user
    campaigns = Campaign.objects.filter(lists__user=request.user).distinct()

    # Optional: Add filtering and sorting
    search_query = request.GET.get('q')
    if search_query:
        campaigns = campaigns.filter(name__icontains=search_query)

    return render(request, 'campaign/campaign_list.html', {'campaigns': campaigns})

@login_required
def start_campaign(request, campaign_id):
    """
    Starts the campaign, initiates phone calls, and sends messages (if applicable).
    """
    # Get campaign object
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)

    # Check if the campaign is already started or sent
    if campaign.status in ['sent', 'scheduled']:
        messages.error(request, "This campaign has already been started or sent.")
        return redirect('contact:campaign_list')

    # Capture the agent ID from the POST request
    if request.method == 'POST':
        agent_id = request.POST.get('agent')

        if not agent_id:
            messages.error(request, "No agent selected.")
            return redirect('contact:campaign_detail', campaign_id=campaign.id)

        agent = get_object_or_404(Agent, id=agent_id, user=request.user)

        # Update campaign status to 'scheduled' and assign the selected agent
        campaign.status = 'scheduled'
        # campaign.agent = agent  # Store the selected agent in the campaign
        campaign.save()

        # Get Twilio service details
        twilio = ServiceDetail.objects.filter(user=request.user, service_name='twilio').first()
        if not twilio:
            messages.error(request, "Twilio service details not found.")
            return redirect('contact:campaign_list')

        client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)

        try:
            # Loop through the recipients and initiate calls
            for contact in campaign.get_recipients():
                phone_number = contact.phone_numbers.first()  # Assuming each contact has at least one phone number
                if not phone_number:
                    continue

                # Create PhoneCall object for each contact
                phone_call = PhoneCall.objects.create(
                    phone_number=phone_number.phone_number,
                    call_status='pending',
                    user=request.user,
                    agnt_id=agent.id,  # Using the selected agent
                    campaign=campaign
                )

                # Initiate the call via Twilio
                try:
                    call = client.calls.create(
                        url=f'{request.scheme}://{request.get_host()}/call/start_twilio_stream/{request.user.id}/{agent.id}/',
                        to=phone_call.phone_number,
                        from_=twilio.decrypted_twilio_phone,
                        record=True,
                        method='POST',
                        status_callback=f'{request.scheme}://{request.get_host()}/call/call_status_callback/{phone_call.id}/',
                        status_callback_method='POST',
                        status_callback_event=["initiated", "ringing", "answered", "completed"]
                    )
                    phone_call.call_status = 'initiated'
                    phone_call.twilio_call_id = call.sid
                    phone_call.save()
                    messages.success(request, f"Call initiated successfully for {phone_number.phone_number}.")
                except Exception as e:
                    phone_call.call_status = 'failed'
                    phone_call.save()
                    messages.error(request, f"Error initiating call to {phone_number.phone_number}: {str(e)}")

            # If all calls are initiated
            messages.success(request, "All calls for the campaign have been successfully initiated.")
        
        except Exception as e:
            campaign.status = 'draft'
            campaign.save()
            messages.error(request, f"An error occurred while starting the campaign: {str(e)}")

        return redirect('contact:campaign_list')

    # GET request handling (in case no agent is selected or campaign is in draft)
    return render(request, 'new/campaign_detail.html', {'campaign': campaign})