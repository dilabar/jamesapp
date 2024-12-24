from django.shortcuts import render, redirect ,  get_object_or_404
from django.core.paginator import Paginator
from django.views.generic import ListView
from agent.models import Contact
from agent.forms import *
import openpyxl
from django.contrib import messages
from django.db import IntegrityError


def contact_list(request):
    contacts = Contact.objects.all()
    
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



def add_contact(request):
    all_lists = List.objects.all()
    all_campaigns = Campaign.objects.all()

    if request.method == 'POST':
        contact_form = ContactForm(request.POST, request.FILES)
        email_form = EmailForm(request.POST)
        phone_form = PhoneNumberForm(request.POST)
        selected_lists = request.POST.getlist('lists')
        selected_campaigns = request.POST.getlist('campaigns')

        if contact_form.is_valid() and email_form.is_valid() and phone_form.is_valid():
            # Save the contact
            contact = contact_form.save()

            # Save the associated emails and phone numbers
            email = email_form.save(commit=False)
            phone_number = phone_form.save(commit=False)

            email.contact = contact
            phone_number.contact = contact

            email.save()
            phone_number.save()

            # Associate contact with selected lists
            for list_id in selected_lists:
                list_obj = get_object_or_404(List, id=list_id)
                list_obj.contacts.add(contact)

            # Associate contact with selected campaigns
            for campaign_id in selected_campaigns:
                campaign_obj = get_object_or_404(Campaign, id=campaign_id)
                campaign_obj.individual_contacts.add(contact)

            return redirect('contact:contact_list')  # Redirect to the contact list page
    else:
        contact_form = ContactForm()
        email_form = EmailForm()
        phone_form = PhoneNumberForm()

    return render(request, 'new/add_contact.html', {
        'contact_form': contact_form,
        'email_form': email_form,
        'phone_form': phone_form,
        'all_lists': all_lists,
        'all_campaigns': all_campaigns
    })





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
            new_list = List.objects.create(name=name, description=description)
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
            'contacts': Contact.objects.all(),  # Pass contacts for the form
        })


def list_overview(request):
    lists = List.objects.all()
    context = {'lists': lists}
    return render(request, 'new/list_overview.html', context)

def list_detail(request, list_id):
    list_obj = get_object_or_404(List, id=list_id)
    return render(request, 'new/list_detail.html', {'list': list_obj})



def create_campaign(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        status = request.POST.get('status')
        scheduled_at = request.POST.get('scheduled_at')

        # Create campaign
        campaign = Campaign.objects.create(
            name=name,
            subject=subject,
            content=content,
            status=status,
            scheduled_at=scheduled_at
        )

        # Add lists to the campaign
        list_ids = request.POST.getlist('lists')
        for list_id in list_ids:
            list_obj = List.objects.get(id=list_id)
            campaign.lists.add(list_obj)

        # Add individual contacts
        contact_ids = request.POST.getlist('contacts')
        for contact_id in contact_ids:
            contact = Contact.objects.get(id=contact_id)
            campaign.individual_contacts.add(contact)

        return redirect('contact:campaign_detail', campaign_id=campaign.id)
    
    lists = List.objects.all()
    contacts = Contact.objects.all()
    return render(request, 'new/create_campaign.html', {'lists': lists, 'contacts': contacts})



def campaign_detail(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return render(request, 'new/campaign_detail.html', {'campaign': campaign})