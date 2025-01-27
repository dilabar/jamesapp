import threading
from django.shortcuts import render, redirect ,  get_object_or_404
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.generic import ListView
from requests import request
from agent.forms import *
import openpyxl
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from twilio.rest import Client
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
import json
from django.utils import timezone
import csv
from django.db import transaction
from contact.forms import CampaignForm, ContactForm, EmailForm, ExcelUploadForm, PhoneNumberForm
from contact.models import *
from datetime import datetime
import pandas as pd

from .task import process_bulk_action
from .forms import CustomFieldForm, ExcelUploadForm
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status



def contact_list(request):
    all_lists = List.objects.filter(user = request.user).order_by('created_at')
    all_campaigns = Campaign.objects.filter(lists__user=request.user).distinct().order_by('created_at')

    if request.user.is_agency():

        contacts = Contact.objects.filter(user__in=request.user.get_all_subaccounts()).order_by('created_at')
    else:
        contacts = Contact.objects.filter(user=request.user).order_by('created_at')

    
    # Pagination setup
    paginator = Paginator(contacts, 10)  # Show 10 contacts per page
    page_number = request.GET.get('page')  # Get the current page number
    page_obj = paginator.get_page(page_number)  # Get the contacts for the current page
    
    # Prepare context
    context = {
        'page_obj': page_obj,
        'contacts': contacts,  # You can also pass the full list if needed elsewhere
        'page_range': paginator.page_range,  # The range of page numbers
        'page_number': page_obj.number, 
        'all_lists': all_lists,
        'all_campaigns': all_campaigns, # Current page number
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
            lists = data.get('lists', [])  # Get the list of selected lists

            # Create the contact instance
            contact = Contact.objects.create(
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                contact_type=contact_type,
                time_zone=time_zone,
                created_at=timezone.now()
            )

            # Process emails and save
            for email, is_primary in emails.items():
                Email.objects.create(
                    contact=contact,
                    user=request.user,
                    email=email.strip(),
                    is_primary=is_primary == 1  # Mark active if primary
                )

            # Process phone numbers and save
            for phone_id, phone_info in phone_data.items():
                PhoneNumber.objects.create(
                    contact=contact,
                    user=request.user,
                    phone_number=str(phone_id).strip(),
                    country_code=phone_info.get('country_code', '').strip(),
                    is_primary=phone_info.get('primary', 0) == 1,  # Mark active if primary
                )

            # Associate contact with selected lists
            for list_id in lists:
                list_obj = get_object_or_404(List, id=list_id, user=request.user)
                list_obj.contacts.add(contact)  # Add the contact to the list

            contact.save()  # Save contact after associating lists

            # Example response
            return JsonResponse({'status': 'success', 'message': 'Contact added successfully!'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid HTTP method'}, status=405)

def upload_excel(request):
    if request.method == 'POST' and request.FILES['file_upload']:
        file = request.FILES['file_upload']
        
        # Open the Excel file
        workbook = openpyxl.load_workbook(excel_file)
        sheet = workbook.active
        
        # Iterate through rows in the Excel file
        for row in sheet.iter_rows(min_row=2, values_only=True):  # Start from row 2 (skip headers)
            print(f"Processing row: First Name: {row[0]}, Last Name: {row[1]}, Email: {row[2]}, Phone: {row[3]}, Type: {row[4]}, Time Zone: {row[5]}")
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


def extract_file(request):
    if request.method == 'POST' and request.FILES.get('file_upload'):
        uploaded_file = request.FILES['file_upload']
        # print("uploaded_file", uploaded_file)
        # Check file format
        file_name = uploaded_file.name
        if not (file_name.endswith('.csv') or file_name.endswith('.xlsx') or file_name.endswith('.xls')):
            messages.error(request, 'Invalid file format. Please upload a CSV or Excel file.')
            return redirect('contact:contact_list')

        try:
            # Process CSV file
            if file_name.endswith('.csv'):
                decoded_file = uploaded_file.read().decode('utf-8').splitlines()
                reader = csv.reader(decoded_file)
                headers = next(reader)  # Extract headers
                header_variables = [
                    header.strip().lower().replace(' ', '_') for header in headers
                ]
                processed_rows = process_csv_rows(reader, headers)
                # check = "csg"
            
            # Process Excel file
            elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
                excel_data = pd.read_excel(uploaded_file)  # Read Excel file using pandas
                print("excel_data", excel_data)
                headers = list(excel_data.columns)  # Extract headers
                header_variables = [
                    header.strip().lower().replace(' ', '_') for header in headers
                ]
                processed_rows = process_excel_rows(excel_data)
                # check = "excel"
            # print({
            #         'check': check,
            #         'headers': headers,
            #         'header_variables': header_variables,
            #         'values': processed_rows,
            #     })
            # Return response with extracted data
            return JsonResponse({
                'status': 'success',
                'data': {
                    'headers': headers,
                    'header_variables': header_variables,
                    'values': processed_rows,
                }
            })

        except Exception as e:
            messages.error(request, f"An error occurred while processing the file: {str(e)}")
            return redirect('agent:contact_list')

    return render(request, 'new/upload_contact.html', {'form': ExcelUploadForm()})


def process_excel_rows(excel_data):
    return {
        header: [
            str(value) if header.lower().strip() == "phone number" and pd.notna(value) else (None if pd.isna(value) else value)
            for value in excel_data[header]
        ]
        for header in excel_data.columns
    }


def process_csv_rows(reader, headers):
    # Initialize a dictionary with headers as keys and empty lists as values
    processed_rows = {header: [] for header in headers}
    
    with transaction.atomic():
        for row_idx, row in enumerate(reader, start=2):  # Start from the second row
            try:
                # Append each value in the row to the corresponding header key
                for i, header in enumerate(headers):
                    processed_rows[header].append(row[i].strip() if row[i] else None)
            except Exception as e:
                # Log a warning and skip the row if an error occurs
                messages.warning(request, f"Row {row_idx}: Error processing row. Skipping. ({str(e)})")
                continue
    
    return processed_rows



def create_bulk_contacts(request):
    if request.method == "POST":
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)
            headers = data.get("headers", [])
            header_variables = data.get("header_variables", [])
            processed_data = data.get("data", {})
            selected_option = data.get("selected_option")

            # print("Headers:", headers)
            # print("Header Variables:", header_variables)
            # print("Processed Data:", processed_data)

            email_set = set()  # Track processed emails to avoid duplication

            for variable, values in processed_data.items():
                # Ensure values are a list
                if isinstance(values, str):
                    value_list = values.split(", ")
                elif isinstance(values, list):
                    value_list = values
                else:
                    raise ValueError(f"Unexpected data type for values: {type(values)}")

                for i, value in enumerate(value_list):
                    # Extract individual data for this contact
                    first_name = (
                        processed_data.get("first_name", [None])[i]
                        if "first_name" in processed_data else None
                    )
                    last_name = (
                        processed_data.get("last_name", [None])[i]
                        if "last_name" in processed_data else None
                    )
                    email = (
                        processed_data.get("email", [None])[i]
                        if "email" in processed_data else None
                    )
                    phone = (
                        processed_data.get("phone_number", [None])[i]
                        if "phone_number" in processed_data else None
                    )

                    if email and email not in email_set:  # Check if email is provided and not processed yet
                        email_set.add(email)  # Add email to the processed set

                        # Check if a contact with this email already exists
                        contact = Contact.objects.filter(emails__email=email).first()

                        if contact:
                            # Update existing contact
                            contact.first_name = first_name or contact.first_name
                            contact.last_name = last_name or contact.last_name
                            contact.updated_at = timezone.now()  # Update timestamp
                            contact.save()
                            print(f"Updated contact: {email}")
                        else:
                            # Create a new contact
                            contact = Contact.objects.create(
                                user=request.user,
                                first_name=first_name,
                                last_name=last_name,
                                contact_type="bulk_import",
                                time_zone="UTC",
                                created_at=timezone.now(),
                            )

                        # Ensure the email object is created or updated
                        Email.objects.update_or_create(
                            contact=contact,
                            email=email,
                            defaults={"user": request.user, "is_primary": True},
                        )

                        # Ensure the phone number object is created or updated
                        if phone:
                            PhoneNumber.objects.update_or_create(
                                contact=contact,
                                user=request.user,
                                phone_number=phone,
                                defaults={
                                    "is_primary": True,
                                    "country_code": None,  # Adjust as needed
                                },
                            )

            return JsonResponse({"message": "Contacts processed successfully!"}, status=201)

        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=405)


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
    if request.user.is_agency():
        agdetail=Agent.objects.filter(user=request.user)
    else:
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
        print("hh")
        # Update campaign status to 'scheduled' and assign the selected agent
        campaign.status = 'sent'
        # campaign.triggers=datetime.now()
        campaign.triggers = {
        'sent_at': timezone.now().isoformat()
        }
        # campaign.agent = agent  # Store the selected agent in the campaign

        # Get Twilio service details
        twilio = ServiceDetail.objects.filter(user=request.user, service_name='twilio').first()
        if not twilio:
            messages.error(request, "Twilio service details not found.")
            return redirect('contact:campaign_list')

        client = Client(twilio.decrypted_account_sid, twilio.decrypted_api_key)

        try:
            # Loop through the recipients and initiate calls
            for contact in campaign.get_recipients():
                phone_number = contact.phone_numbers.filter(is_primary=True).first()  # Assuming each contact has at least one phone number
                print("ggg phobe conatc",phone_number)
                if not phone_number:
                    continue

                # Create PhoneCall object for each contact
                country_code = phone_number.country_code or ''
                phone_number_str = f"{country_code}{phone_number.phone_number}".strip()
                phone_call = PhoneCall.objects.create(
                    phone_number=phone_number_str,
                    call_status='pending',
                    user=request.user,
                    agnt_id=agent.id,  # Using the selected agent
                    campaign=campaign,
                    contact=contact
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
            campaign.save()

            # If all calls are initiated
            messages.success(request, "All calls for the campaign have been successfully initiated.")
        
        except Exception as e:
            campaign.status = 'draft'
            campaign.save()
            messages.error(request, f"An error occurred while starting the campaign: {str(e)}")

        return redirect('contact:campaign_list')

    # GET request handling (in case no agent is selected or campaign is in draft)
    return render(request, 'new/campaign_detail.html', {'campaign': campaign})





@login_required
def contact_details(request, id):
    # Fetch the contact by ID
    contact = get_object_or_404(Contact, id=id)

    # Fetch all contacts ordered by ID
    contacts = Contact.objects.all().order_by('id')
    total_contacts = contacts.count()
    
    # Get the current contact's position
    current_position = list(contacts).index(contact) + 1  # Add 1 for 1-based indexing

    # Fetch the previous and next contacts based on ID
    previous_contact = Contact.objects.filter(id__lt=contact.id).order_by('-id').first()
    next_contact = Contact.objects.filter(id__gt=contact.id).order_by('id').first()
    
    # Retrieve emails and phone numbers for the contact
    emails = contact.emails.all()
    phone_numbers = contact.phone_numbers.all()
    
    # Prepare the interactions list
    interactions = []
    phone_calls = PhoneCall.objects.filter(contact=contact)
    for phone_call in phone_calls:
        interactions.append({
            'type': 'Agent call',
            'title': f"Phone Call - {phone_call.phone_number} - {phone_call.campaign.name}",
            'timestamp': phone_call.timestamp,
            'object': phone_call.id,
        })
    
    # Handle POST request for updating the contact
    if request.method == 'POST':
        # Update primary email
        selected_email_id = request.POST.get('primary_email')
        if selected_email_id:
            for email in emails:
                email.is_primary = (str(email.id) == selected_email_id)
                email.save()
        
        # Update primary phone number
        selected_phone_id = request.POST.get('primary_phone')
        if selected_phone_id:
            for phone in phone_numbers:
                phone.is_primary = (str(phone.id) == selected_phone_id)
                phone.save()
        
        # Update other contact fields
        contact.first_name = request.POST.get('first_name')
        contact.last_name = request.POST.get('last_name')
        contact.email = request.POST.get('email')
        contact.phone = request.POST.get('phone')
        contact.contact_type = request.POST.get('contact_type')
        contact.save()
        
        # Redirect to the same page after update
        return redirect('contact:contact_details', id=contact.id)
    
    context = {
        'contact': contact,
        'emails': emails,
        'phone_numbers': phone_numbers,
        'interactions': interactions,
        'previous_contact': previous_contact,
        'next_contact': next_contact,
        'current_position': current_position,
        'total_contacts': total_contacts,
    }
    return render(request, 'contact/contact_detail.html', context)


@login_required
def bulk_upload(request):
    if request.method == 'POST' and request.FILES.get('csvFile'):
        csv_file = request.FILES['csvFile']
        headers = []
        try:
            # Read CSV headers
            csv_reader = csv.reader(csv_file.read().decode('utf-8').splitlines())
            headers = next(csv_reader)  # Get the first row as headers
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

        # Get predefined and user custom fields
        predefined_fields = CustomField.objects.filter(is_predefined=True)
        user_custom_fields = CustomField.objects.filter(is_predefined=False, user=request.user)
        # Merge the predefined and user-defined fields
        custom_fields = list(predefined_fields) + list(user_custom_fields)

        # Prepare data to send back to frontend
        custom_field_data = [
            {
                'id': field.id,
                'name': field.name,
                'is_predefined': field.is_predefined
            }
            for field in custom_fields
        ]
        return JsonResponse({'headers': headers,'fields': custom_field_data})

    return JsonResponse({'error': 'Invalid request'}, status=400)

def add_custom_field(request):
    if request.method == 'POST':
        form = CustomFieldForm(request.POST)
        if form.is_valid():
            custom_field = form.save(commit=False)
            custom_field.user = request.user  # Associate the field with the logged-in user
            custom_field.save()
            messages.success(request, 'Custom field added successfully.')
            return redirect('contact:add_custom_field')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomFieldForm()

    return render(request, 'custom/add_custom_field.html', {'form': form})

@login_required
def bulk_action_list(request):
    # Fetch action list for the logged-in user
    actionlist = BulkAction.objects.filter(user=request.user).order_by('-created_at')

    # # Optional: Add filtering and sorting
    # search_query = request.GET.get('q')
    # if search_query:
    #     campaigns = campaigns.filter(name__icontains=search_query)

    return render(request, 'bulk_action/list.html', {'list': actionlist})
