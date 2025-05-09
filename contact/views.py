import threading
import uuid
from threading import Thread
from django.forms import model_to_dict
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
from jamesapp.tasks import pause_task, process_campaign_calls, resume_task
from jamesapp.utils import contact_to_serializable_dict, log_activity
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
from django.db.models import Sum, Count, Q,Value,Case, When,F,CharField
from django.db.models.functions import Coalesce, Concat
from django.utils.html import escape

from .task import process_bulk_action
from .forms import CustomFieldForm, ExcelUploadForm,ListForm
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
import re  # For phone number validation

from django.utils.timesince import timesince


@login_required
def contact_list(request):
    # all_lists = List.objects.filter(user = request.user).order_by('created_at')
    # all_campaigns = Campaign.objects.filter(lists__user=request.user).distinct().order_by('created_at')

    # if request.user.is_agency():

    #     contacts = Contact.objects.filter(user__in=request.user.get_all_subaccounts()).order_by('created_at')
    # else:
    #     contacts = Contact.objects.filter(user=request.user).order_by('created_at')

    
    # # Pagination setup
    # paginator = Paginator(contacts, 10)  # Show 10 contacts per page
    # page_number = request.GET.get('page')  # Get the current page number
    # page_obj = paginator.get_page(page_number)  # Get the contacts for the current page
    
    
    # Prepare context
    context = {
        # 'page_obj': page_obj,
        # 'contacts': contacts,  # You can also pass the full list if needed elsewhere
        # 'page_range': paginator.page_range,  # The range of page numbers
        # 'page_number': page_obj.number, 
        # 'all_lists': all_lists,
        # 'all_campaigns': all_campaigns, # Current page number
    }
    
    return render(request, 'new/contact_list.html', context)
@login_required
def contact_data(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    if request.user.is_agency():
        queryset = Contact.objects.filter(user__in=request.user.get_all_subaccounts())
    else:
        queryset = Contact.objects.filter(user=request.user)

    if search_value:
        queryset = queryset.filter(
            Q(first_name__icontains=search_value) |
            Q(last_name__icontains=search_value) |
            Q(emails__email__icontains=search_value) |
            Q(phone_numbers__phone_number__icontains=search_value)
        ).distinct()

    total_records = queryset.count()
    queryset = queryset.order_by('-created_at')[start:start+length]

    data = []
    for contact in queryset:
        emails = contact.emails.all()
        phones = contact.phone_numbers.all()

        email_list = [
            f"{email.email}{' (Primary)' if email.is_primary else ''}"
            for email in emails
        ]
        phone_list = [
            f"{phone.phone_number}{' (Primary)' if phone.is_primary else ''}"
            for phone in phones
        ]
        actions = f'''
           
            <button class="btn btn-sm btn-danger del-con" data-id="{contact.id}">Delete</button>
        '''
        full_name = f"{contact.first_name} {contact.last_name or ''}".strip().title()
        contact_detail_url = reverse('contact:contact_details', args=[contact.id])
        data.append({
            'name': f'<a href="{contact_detail_url}">{full_name}</a>',
            'email': ', '.join(email_list) or 'No emails',
            'phone': ', '.join(phone_list) or 'No phone numbers available',
            'created_at': contact.created_at.strftime('%Y-%m-%d %H:%M'),
            'created_ago': f"{timesince(contact.created_at)} ago",
            'contact_type': contact.contact_type if contact.contact_type else 'NA',
            'timezone': contact.time_zone if contact.time_zone else 'NA',
            # 'lists': ', '.join([lst.name for lst in contact.lists.all()]) if hasattr(contact, 'lists') else '',
            # 'campaigns': ', '.join([camp.name for camp in contact.campaigns.all()]) if hasattr(contact, 'campaigns') else '',
            'actions': actions
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data,
    })






@login_required
def add_contact(request):
    """Handles creating a new contact with validation and error handling."""
    all_lists = List.objects.filter(user=request.user)
    all_campaigns = Campaign.objects.filter(lists__user=request.user).distinct()

    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Extract and validate first & last name
            first_name = data.get('firstName', '').strip()
            last_name = data.get('lastName', '').strip()
            
            if not first_name or len(first_name) > 50:
                return JsonResponse({'status': 'error', 'message': 'First name is required and must be under 50 characters.'}, status=400)
            if len(last_name) > 50:
                return JsonResponse({'status': 'error', 'message': 'Last name must be under 50 characters.'}, status=400)

            # Extract and validate emails
            emails = data.get('emails', {})
            valid_emails = {}

            for email, is_primary in emails.items():
                email = email.strip()
                try:
                    validate_email(email)  # Django's built-in email validator
                    valid_emails[email] = is_primary
                except ValidationError:
                    return JsonResponse({'status': 'error', 'message': f'Invalid email: {email}'}, status=400)

            if not valid_emails:
                return JsonResponse({'status': 'error', 'message': 'At least one valid email is required.'}, status=400)

            # Extract and validate phone numbers
            phone_data = data.get('phoneData', {})
            valid_phone_numbers = {}

            phone_regex = re.compile(r'^\+?[1-9]\d{7,14}$')  # Simple regex for international numbers

            for phone_id, phone_info in phone_data.items():
                phone_number = str(phone_id).strip()
                country_code = phone_info.get('country_code', '').strip()
                
                if not phone_regex.match(phone_number):
                    return JsonResponse({'status': 'error', 'message': f'Invalid phone number: {phone_number}'}, status=400)
                
                valid_phone_numbers[phone_number] = phone_info

            # Extract and validate contact type & time zone
            contact_type = data.get('contactType', '').strip()
            time_zone = data.get('timeZone', '').strip()

            if not contact_type:
                return JsonResponse({'status': 'error', 'message': 'Contact type is required.'}, status=400)
            if not time_zone:
                return JsonResponse({'status': 'error', 'message': 'Time zone is required.'}, status=400)

            # Validate lists
            lists = data.get('lists', [])
            valid_lists = []

            for list_id in lists:
                try:
                    list_obj = get_object_or_404(List, id=list_id, user=request.user)
                    valid_lists.append(list_obj)
                except Exception:
                    return JsonResponse({'status': 'error', 'message': f'Invalid or unauthorized list ID: {list_id}'}, status=400)

            # Create the contact instance
            contact = Contact.objects.create(
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                contact_type=contact_type,
                time_zone=time_zone,
                created_at=timezone.now()
            )

            # Save emails
            for email, is_primary in valid_emails.items():
                Email.objects.create(
                    contact=contact,
                    user=request.user,
                    email=email,
                    is_primary=is_primary == 1
                )

            # Save phone numbers
            for phone_number, phone_info in valid_phone_numbers.items():
                PhoneNumber.objects.create(
                    contact=contact,
                    user=request.user,
                    phone_number=phone_number,
                    country_code=phone_info.get('country_code', ''),
                    is_primary=phone_info.get('primary', 0) == 1
                )

            # Associate with lists
            for list_obj in valid_lists:
                list_obj.contacts.add(contact)

            contact.save()
                        # Serialize custom field info for logging
            contact_data = contact_to_serializable_dict(contact)

            # Log the activity
          
            log_activity(request.user, f"Created a new contact: {contact.first_name} {contact.last_name}, Type: {contact.contact_type}",additional_info=contact_data)

            return JsonResponse({'status': 'success', 'message': 'Contact added successfully!'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid HTTP method'}, status=405)

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
    # if request.user.is_agency():

    #     listsd = List.objects.filter(user__in=request.user.get_all_subaccounts())
    #     print(request.user.get_all_subaccounts())
    # else:
    #     listsd = List.objects.filter(user=request.user)

    context = {}
    return render(request, 'list/list.html', context)

def list_data(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    if request.user.is_agency():
        queryset = List.objects.filter(user__in=request.user.get_all_subaccounts())
    else:
        queryset = List.objects.filter(user=request.user)

    if search_value:
        queryset = queryset.filter(name__icontains=search_value)

    total = queryset.count()
    queryset = queryset.order_by('-created_at')[start:start + length]

    data = []
    for index, lst in enumerate(queryset, start=start + 1):
        detail_url = reverse('contact:list_detail', args=[lst.id])
        edit_url = reverse('contact:edit_list', args=[lst.id])
        delete_url = reverse('contact:delete_list', args=[lst.id])

        actions = f'''
            <a href="{detail_url}" class="btn btn-primary btn-sm">View Details</a>
            <a href="{edit_url}" class="btn btn-secondary btn-sm">Edit</a>
            <a href="{delete_url}" class="btn btn-danger btn-sm" 
               onclick="return confirm('Are you sure you want to delete this list?');">Delete</a>
        '''

        data.append({
            "index": index,
            "name": lst.name.title(),
            "count": lst.contacts.count(),
            "created_at": lst.created_at.strftime("%Y-%m-%d %H:%M"),
            "action": actions
        })

    return JsonResponse({
        "draw": draw,
        "recordsTotal": total,
        "recordsFiltered": total,
        "data": data
    })

def list_detail(request, list_id):
    list_obj = get_object_or_404(List, id=list_id)
   

    return render(request, 'list/list_detail.html', {
        'list': list_obj,
      
    })
@login_required
def list_detail_data(request, list_id):
    list_obj = get_object_or_404(List, id=list_id)
    search_value = request.GET.get('search[value]', '')
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))

    queryset = Contact.objects.filter(lists=list_obj).prefetch_related('emails', 'phone_numbers')

    if search_value:
        queryset = queryset.filter(
            Q(first_name__icontains=search_value) |
            Q(last_name__icontains=search_value) |
            Q(emails__email__icontains=search_value) |
            Q(phone_numbers__phone_number__icontains=search_value)
        ).distinct()

    total_records = queryset.count()
    queryset = queryset[start:start + length]

    data = []
    for i, contact in enumerate(queryset, start=start + 1):

        email_str = ', '.join([
            f"{email.email}{' (Primary)' if email.is_primary else ''}"
            for email in contact.emails.all()
        ]) or 'No emails'

        phone_str = ', '.join([
            f"{phone.phone_number}{' (Primary)' if phone.is_primary else ''}"
            for phone in contact.phone_numbers.all()
        ]) or 'No phone numbers'

        data.append({
            'index': i,
            'name': f"{contact.first_name} {contact.last_name or ''}".strip(),
            'email': email_str,
            'phone': phone_str,
            'created_at': contact.created_at.strftime('%Y-%m-%d %H:%M'),
            'created_ago':f"{timesince(contact.created_at)} ago",  # optional if you pass timeago string
            'contact_type': contact.contact_type if contact.contact_type else 'NA',
            'timezone': contact.time_zone or '',
            'actions': f'''
                <a href="{reverse('contact:contact_details', args=[contact.id])}" class="btn btn-sm btn-info">View</a>
                <a href="{reverse('contact:delete_contact', args=[contact.id])}" class="btn btn-sm btn-danger" onclick="return confirm('Are you sure?')">Delete</a>
            '''
        })

    return JsonResponse({
        'draw': int(request.GET.get('draw', 1)),
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })



@login_required
def create_campaign(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST, user=request.user)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.user = request.user  # Assign logged-in user
            campaign.save()
            form.save_m2m()  # Save Many-to-Many relationships
            messages.success(request, "Campaign created successfully!")
            return redirect('contact:campaign_detail', campaign_id=campaign.id)
        else:
            print(form.errors)
            messages.error(request, "There was an error creating the campaign.")
    
    else:
        form = CampaignForm(user=request.user)

    return render(request, 'campaign/create_campaign.html', {'form': form})


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
def campaign_detail_v1(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)

    # Get agent detail for agency or parent agency
    if request.user.is_agency():
        agdetail = Agent.objects.filter(user=request.user)
    else:
        agdetail = Agent.objects.filter(user=request.user.parent_agency)

    # Query only for call analytics — actual calls will load in DataTable API
    phonecall_qs = PhoneCall.objects.filter(campaign_id=campaign_id)
        # Total calls placed (Total count - Pending calls)
    # pending_calls = phonecall_qs.filter(call_status__in=['pending']).count()



    call_analytics = phonecall_qs.aggregate(
        calls_placed=Count('id'),
        calls_answered=Count('id', filter=Q(call_status__in=['in-progress', 'completed'])),
        calls_failed=Count('id', filter=Q(call_status__in=['failed', 'no-answer', 'busy', 'canceled', 'initiated'])),
        calls_completed=Count('id', filter=Q(call_status='completed')),
        calls_pending=Count('id', filter=Q(call_status='pending')),
        total_voice_minutes=Coalesce(Sum('call_duration'), Value(0))
    )

    # Format total voice minutes to "Xm Ys"
    total_secs = call_analytics['total_voice_minutes'] or 0
    call_analytics['total_voice_minutes'] = f"{total_secs // 60}m {total_secs % 60}s"
    call_analytics['calls_placed'] = call_analytics['calls_placed'] - call_analytics['calls_pending']

    context = {
        'campaign': campaign,
        'agdetail': agdetail,
        'call_analytics': call_analytics,
    }
    return render(request, 'campaign/campaign_detail.html', context)
@login_required
def campaign_calls_data_api(request, campaign_id):
    search = request.GET.get('search[value]', '')
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    order_column_index = request.GET.get('order[0][column]', '0')
    order_column = request.GET.get(f'columns[{order_column_index}][data]', 'id')
    order_dir = request.GET.get('order[0][dir]', 'asc')

    # Map 'contact_name' to the annotated full_name field
    if order_column == 'contact_name':
        order_column = 'full_name'
    
    order = order_column if order_dir == 'asc' else f'-{order_column}'

    phonecalls = (
        PhoneCall.objects
        .filter(campaign_id=campaign_id)
        .select_related('contact')
        .annotate(
            call_duration_fixed=Coalesce(F('call_duration'), Value(0)),
            is_call_answered=Case(
                When(call_status__in=['in-progress', 'completed'], then=Value(True)),
                default=Value(False),
            ),
            full_name=Concat(
                F('contact__first_name'),
                Value(' '),
                F('contact__last_name'),
                output_field=CharField()
            )
        )
    )

    if search:
        phonecalls = phonecalls.filter(
            Q(contact__first_name__icontains=search) |
            Q(contact__last_name__icontains=search) |
            Q(phone_number__icontains=search)
        )

    total = phonecalls.count()

    phonecalls = phonecalls.order_by(order)

    paginator = Paginator(phonecalls, length)
    page = paginator.get_page(start // length + 1)

    status_map = {
        "initiated": ("badge-light-light", "The call has been created but not yet started dialing."),
        "queued": ("badge-light-warning", "The call is waiting in the queue to be processed."),
        "ringing": ("badge-light-info", "The recipient's phone is ringing."),
        "in-progress": ("badge-light-primary", "The call has been answered and is currently active."),
        "completed": ("badge-light-success", "The call has ended successfully."),
        "busy": ("badge-light-danger", "The recipient’s phone is busy."),
        "failed": ("badge-light-dark", "The call could not be initiated."),
        "no-answer": ("badge-light-secondary", "The call rang but was not answered."),
        "canceled": ("badge-light-secondary", "The call was canceled."),
    }

    data = []
    for call in page.object_list:
        contact_name = escape(f"{call.contact.first_name} {call.contact.last_name}") if call.contact else "Unknown"
        contact_url = reverse('contact:contact_details', args=[call.contact.id]) if call.contact else "#"
        detail_url = reverse('agent:call_detail', args=[call.id])

        status_class, status_desc = status_map.get(call.call_status, ("badge-light-secondary", "No status description available"))
        call_status_html = f"""
        <a href="#" class="badge {status_class}" data-bs-toggle="tooltip" data-bs-title="{escape(status_desc)}">
            {call.call_status.upper()}
        </a>
        """

        data.append({
            'contact_name': f'<a href="{contact_url}">{contact_name}</a>',
            'phone_number': escape(call.phone_number),
            'is_call_answered': 'Yes' if call.is_call_answered else 'No',
            'call_duration': f"{call.call_duration_fixed // 60}m {call.call_duration_fixed % 60}s",
            'call_status': call_status_html,
            'detail': f'<a href="{detail_url}">Call Detail</a>',
        })

    return JsonResponse({
        'data': data,
        'recordsTotal': total,
        'recordsFiltered': total if not search else page.paginator.count,
        'draw': int(request.GET.get('draw', 1)),
    })
@login_required
def revoke_campaign_task(request, campaign_id):
    # Revoke the campaign's task
    campaign = get_object_or_404(Campaign, id=campaign_id)
    # Check if the campaign is already paused
    if campaign.status == "paushed":
        messages.info(request, "This campaign is already paused.")
        return redirect('contact:campaign_detail', campaign_id=campaign.id)
    
    task_id = campaign.triggers.get('task_id')
    if not task_id:
        messages.error(request, "No task found for this campaign.")
        return redirect('contact:campaign_detail', campaign_id=campaign.id)
    pause_task(task_id)
    campaign.status = "paushed"
    campaign.save(update_fields=['status'])

    messages.success(request, f"Task {task_id} has been successfully paused.")
    return redirect('contact:campaign_detail', campaign_id=campaign.id)
@login_required
def restart_campaign_task(request, campaign_id):
    # Revoke the campaign's task
    campaign = get_object_or_404(Campaign, id=campaign_id)
    # Check if the campaign is already paused
    if campaign.status == "started":
        messages.info(request, "This campaign is already started.")
        return redirect('contact:campaign_detail', campaign_id=campaign.id)
    # if not task_id:
    #     messages.error(request, "No task found for this campaign.")
    #     return redirect('contact:campaign_detail', campaign_id=campaign.id)
    resume_task(campaign.id,request.user.id,campaign.agent.id)
        # Update campaign status
    campaign.status = "started"
    campaign.save(update_fields=['status'])
    task_id = campaign.triggers.get('task_id')

    messages.success(request, f"Task {task_id} has been successfully Restarted.")
    return redirect('contact:campaign_detail', campaign_id=campaign.id)
@login_required
def start_campaign_view(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    print(campaign.status)
    if campaign.status not in ['draft', 'scheduled']:
        return JsonResponse({"error": "Campaign already started or finished."}, status=400)

    task = process_campaign_calls.delay(campaign.id, request.user.id, campaign.agent.id)
    campaign.status = 'queued'
    campaign.triggers = {'task_id': task.id}
    campaign.save()
    return JsonResponse({"message": "Campaign started. Processing in background.", "task_id": task.id})

# @login_required
# def campaign_list(request):
#     # Fetch campaigns for the logged-in user
#     campaigns = Campaign.objects.filter(lists__user=request.user).distinct()

#     # Optional: Add filtering and sorting
#     search_query = request.GET.get('q')
#     if search_query:
#         campaigns = campaigns.filter(name__icontains=search_query)

#     return render(request, 'campaign/campaign_list.html', {'campaigns': campaigns})
@login_required
def campaign_list(request):
    # # Fetch campaigns for the logged-in user
    # campaigns = Campaign.objects.filter(lists__user=request.user).distinct()

    # # Optional: Add filtering
    # search_query = request.GET.get('q')
    # if search_query:
    #     campaigns = campaigns.filter(name__icontains=search_query)

    # # Add ordering - most recent first
    # campaigns = campaigns.order_by('-created_at')

    # # Pagination
    # paginator = Paginator(campaigns, 5)  # Show 10 campaigns per page
    # page_number = request.GET.get('page')
    # page_obj = paginator.get_page(page_number)

    return render(request, 'campaign/campaign_list.html')

def campaign_data(request):
    draw = request.GET.get('draw')
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 5))
    search_value = request.GET.get('search[value]', '')

    campaigns = Campaign.objects.filter(lists__user=request.user).distinct()

    if search_value:
        campaigns = campaigns.filter(Q(name__icontains=search_value))

    total = campaigns.count()
    campaigns = campaigns.order_by('-created_at')[start:start+length]

    data = []
    for campaign in campaigns:
        view_url = reverse('contact:campaign_detail', args=[campaign.id])
        edit_url = reverse('contact:edit_campaign', args=[campaign.id])
        delete_url = reverse('contact:delete_campaign', args=[campaign.id])
        if campaign.scheduled_at:
            scheduled_display = campaign.scheduled_at.strftime('%b %d, %Y %H:%M')
        else:
            scheduled_display = 'Not Scheduled'
        actions = f'''
            <a href="{view_url}" class="btn btn-sm btn-outline-success" title="View">
                <i class="fa fa-play"></i>
            </a>
            <a href="{edit_url}" class="btn btn-sm btn-outline-warning" title="Edit">
                <i class="icon-pencil-alt"></i>
            </a>
            <a href="{delete_url}" class="btn btn-sm btn-outline-danger" title="Delete"
            onclick="return confirm('Are you sure you want to delete this campaign?');">
                <i class="icon-trash"></i>
            </a>
        '''
        data.append({
            'name': campaign.name.title(),
            'created_at': campaign.created_at.strftime('%b %d, %Y %H:%M'),
            'scheduled_at':scheduled_display,
            'created_ago':f"{timesince(campaign.created_at)} ago",  # optional if you pass timeago string
            'actions': actions,
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total if search_value else total,
        'data': data,
    })

def start_campaign(user, campaign_id):
    """
    Starts the campaign, initiates phone calls, and sends messages (if applicable).
    """
    # Get campaign object
    campaign = get_object_or_404(Campaign, id=campaign_id, user=user)

    # Check if the campaign is already started or sent
    if campaign.status in ['sent', 'scheduled','started']:
        messages.error(request, "This campaign has already been started or sent.")
        return redirect('contact:campaign_list')

    # Capture the agent ID from the POST request
    if request.method == 'POST':
        # agent_id = request.POST.get('agent')

        # if not agent_id:
        #     messages.error(request, "No agent selected.")
        #     return redirect('contact:campaign_detail', campaign_id=campaign.id)

        # agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        print("hh")
        # Update campaign status to 'scheduled' and assign the selected agent
        campaign.status = 'sent'
        # campaign.triggers=datetime.now()
        campaign.triggers = {
        'sent_at': timezone.now().isoformat()
        }
        # campaign.agent = agent  # Store the selected agent in the campaign

        # Get Twilio service details
        twilio = ServiceDetail.objects.filter(user=user, service_name='twilio').first()
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
                    user=user,
                    agnt_id=campaign.agent.id,  # Using the selected agent
                    campaign=campaign,
                    contact=contact
                )

                # Initiate the call via Twilio
                try:
                    call = client.calls.create(
                        url=f'https://{request.get_host()}/call/start_twilio_stream/{user.id}/{campaign.agent.id}/',
                        to=phone_call.phone_number,
                        from_=twilio.decrypted_twilio_phone,
                        record=True,
                        method='POST',
                        status_callback=f'https://{request.get_host()}/call/call_status_callback/{phone_call.id}/',
                        status_callback_method='POST',
                        status_callback_event=["initiated", "ringing", "answered", "completed"]
                    )
                    phone_call.call_status = 'initiated'
                    phone_call.twilio_call_id = call.sid
                    phone_call.save()
                    # messages.success(request, f"Call initiated successfully for {phone_number.phone_number}.")
                except Exception as e:
                    phone_call.call_status = 'failed'
                    phone_call.save()
                    # messages.error(request, f"Error initiating call to {phone_number.phone_number}: {str(e)}")
            campaign.save()

            # If all calls are initiated
            # messages.success(request, "All calls for the campaign have been successfully initiated.")
        
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
            'title': f"Phone Call - {phone_call.phone_number} - {phone_call.campaign}",
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
        contact.time_zone = request.POST.get('time_zone')
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
        raw_data = csv_file.read()
        headers = []
        try:
            # Read CSV headers
                # Try UTF-8 first
            try:
                decoded_data = raw_data.decode('utf-8').splitlines()
            except UnicodeDecodeError:
                # Fallback to latin-1 if UTF-8 fails
                decoded_data = raw_data.decode('latin-1').splitlines()
            # csv_reader = csv.reader(csv_file.read().decode('utf-8').splitlines())
            csv_reader = csv.reader(decoded_data)
            
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
@login_required
def add_custom_field(request):
    if request.method == 'POST':
        form = CustomFieldForm(request.POST)
        if form.is_valid():
            custom_field = form.save(commit=False)
            custom_field.user = request.user  # Associate the field with the logged-in user
            custom_field.save()
            # Serialize custom field info for logging
            custom_field_data = model_to_dict(custom_field)

            # Log the activity
            log_activity(
                request.user, 
                f"Added custom field: {custom_field.name}", 
                additional_info=custom_field_data
            )
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





# @login_required
# def delete_contact(request, id):
#     contact = get_object_or_404(Contact, id=id)
    
#     if request.method == 'POST':
#         contact.delete()
#         return redirect('contact:contact_list')  # Redirect to the contact list page after deletion

#     return redirect('contact:contact_list')  # Redirect if not POST
@csrf_exempt
def delete_contact(request, id):
    """Handles deleting a contact."""
    if request.method == 'POST':
        try:
            # Get the contact and check if it belongs to the logged-in user
            contact = Contact.objects.get(id=id, user=request.user)
            contact_data = contact_to_serializable_dict(contact)
            # Log the activity of deleting the contact
            log_activity(
                request.user, 
                f"Deleted contact: {contact.first_name} {contact.last_name}, Contact ID: {contact.id}", additional_info=contact_data
            )
            
            # Perform the deletion
            contact.delete()
            return JsonResponse({'success': True})
        
        except Contact.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Contact not found.'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
def custom_fields(request):
    # Get all custom fields from the database
    custom_fields = CustomField.objects.all()

    return render(request, 'custom/custom_overview.html', {'custom_fields': custom_fields})
  # Adjust the template name as needed

@login_required
def delete_list(request, list_id):
    # Get the list by ID or return a 404 if not found
    list_to_delete = get_object_or_404(List, id=list_id, user=request.user)
    # list_data = model_to_dict(list_to_delete)
    list_data = model_to_dict(list_to_delete, exclude=['contacts'])
    # Log the activity of deleting the contact
    log_activity(
        request.user, 
        f"Deleted List: {list_to_delete.name}, List ID: {list_to_delete.id}", additional_info=list_data
    )
    # Delete the list
    list_to_delete.delete()

    # Show a success message
    messages.success(request, 'List deleted successfully.')

    # Redirect to the list overview page
    return redirect('contact:list_overview')







@login_required
def delete_campaign(request, campaign_id):
    # Get the campaign or return a 404 if not found
    campaign = get_object_or_404(Campaign, id=campaign_id, lists__user=request.user)
    
    # Delete the campaign
    campaign.delete()
    
    messages.success(request, 'Campaign deleted successfully.')
    return redirect('contact:campaign_list')


@login_required
def delete_custom_field(request, field_id):
    # Retrieve the custom field object by its ID, or return 404 if not found
    custom_field = get_object_or_404(CustomField, id=field_id)
    
    # Delete the object
    custom_field.delete()

    # Redirect back to the custom fields overview page using the correct URL name
    return redirect('contact:custom_fields')



@login_required
def edit_campaign(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)  # Ensure the user owns the campaign

    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('contact:campaign_detail', campaign_id=campaign.id)  # Redirect to detail page after saving
    else:
        form = CampaignForm(instance=campaign, user=request.user)

    return render(request, 'campaign/edit_campaign.html', {'form': form, 'campaign': campaign})




# List Edit View
@login_required
def edit_list(request, list_id):
    list_obj = get_object_or_404(List, id=list_id)

    if request.method == 'POST':
        form = ListForm(request.POST, instance=list_obj)
        if form.is_valid():
            form.save()  # Save the updated list
            return redirect('contact:list_detail', list_id=list_id)  # Redirect to the list detail page
    else:
        form = ListForm(instance=list_obj)  # Pre-fill the form with the existing list data

    context = {'form': form, 'list': list_obj}
    return render(request, 'new/edit_list.html', context)


# List Edit View
@login_required
def edit_list(request, list_id):
    list_obj = get_object_or_404(List, id=list_id)

    if request.method == 'POST':
        form = ListForm(request.POST, instance=list_obj)
        if form.is_valid():
            form.save()  # Save the updated list
            return redirect('contact:list_detail', list_id=list_id)  # Redirect to the list detail page
    else:
        form = ListForm(instance=list_obj)  # Pre-fill the form with the existing list data

    context = {'form': form, 'list': list_obj}
    return render(request, 'new/edit_list.html', context)
@login_required
def select_lists(request):
    search_query = request.GET.get('search', '')  # Get search input
    lists = List.objects.filter(user=request.user)

    if search_query:
        lists = lists.filter(name__icontains=search_query)  # Search filter

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(lists, 10)  # Show 10 lists per page
    page_obj = paginator.get_page(page_number)

    return render(request, 'contact/select_lists.html', {'page_obj': page_obj, 'search_query': search_query})
@login_required
def select_contacts(request):
    query = request.GET.get('search', '')  # Get search query from request
    page_number = request.GET.get('page', 1)  # Get current page

    # Filter contacts by user
    contacts = Contact.objects.filter(user=request.user)

    # Apply search filter if query exists
    if query:
        contacts = contacts.filter(first_name__icontains=query) | contacts.filter(last_name__icontains=query)

    # Paginate results (5 contacts per page)
    paginator = Paginator(contacts, 10)
    page_obj = paginator.get_page(page_number)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'contact/select_contacts.html', {'page_obj': page_obj})

    return render(request, 'contact/select_contacts.html', {'page_obj': page_obj, 'search_query': query})