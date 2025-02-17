# Your task function that runs in a separate thread
import asyncio
import csv
import json
import threading
import chardet

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from .models import BulkAction, Contact, CustomField, Email, List, Note, PhoneNumber
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import Q 
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


def process_in_thread(action_id):
    action = BulkAction.objects.get(id=action_id)
    
    # Simulate processing (replace with your actual task logic)
    try:
        action.status = 'PROCESSING'
        action.save()
        
        if action.action_type == 'IMPORT':
            # Implement import logic here
            pass
        elif action.action_type == 'EXPORT':
            # Implement export logic here
            pass
        elif action.action_type == 'DELETE':
            # Implement delete logic here
            pass
        
        # Mark action as completed after processing
        action.status = 'COMPLETED'
        action.completed_at = timezone.now()
        action.save()
        
    except Exception as e:
        # Handle exceptions and mark as failed
        action.status = 'FAILED'
        action.error_message = str(e)
        action.save()
# def parse_csv(file_path):
#     with open(file_path, mode="r", encoding="utf-8") as file:
#         reader = csv.DictReader(file)
#         return [row for row in reader]
    


def parse_csv(file_path):
    # Detect the file encoding
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        detected_encoding = chardet.detect(raw_data)['encoding']
        print(f"Detected encoding: {detected_encoding}")  # Debugging

    # Read the file using the detected encoding
    try:
        with open(file_path, mode="r", encoding=detected_encoding) as file:
            reader = csv.DictReader(file)
            return [row for row in reader]
    except UnicodeDecodeError:
        # Fallback to latin-1 if the detected encoding fails
        with open(file_path, mode="r", encoding="latin-1") as file:
            reader = csv.DictReader(file)
            return [row for row in reader]
    except Exception as e:
        print(f"Error parsing CSV file: {e}")
        return []
# class BulkActionTriggerView(View):
#     # parser_classes = (MultiPartParser, FormParser)  # To handle file uploads
#     def post(self, request):
#         user = request.user  # Assume user is authenticated
#         csv_file = request.FILES.get('csvFile')
#         field_mappings = request.POST.get('fieldMappings')
#         import_option = request.POST.get('importOption')
#         deduplication = request.POST.get('deduplication')
#         listId = request.POST.get('listId')

#         if not csv_file or not field_mappings or not import_option or not deduplication:
#             return JsonResponse({'error': 'Missing required data'}, status=400)
        
#                 # Convert the field mappings to a Python dict (assumed to be a JSON string)
#         # Parse field mappings
#         try:
#             field_mappings = json.loads(field_mappings)
#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid fieldMappings format. Must be a valid JSON string.'}, status=400)

#         try:
#              # Save the bulk action in the database
#             with transaction.atomic():
#                 bulk_action = BulkAction.objects.create(
#                     user=user,
#                     action_type='IMPORT',
#                     csv_file=csv_file,
#                     data={
#                         'field_mappings': field_mappings,
#                         'importOption': import_option,
#                         'deduplication': deduplication,
#                         'listId':listId
#                     },
#                 )
        
       
        
#             # Trigger background task
#             # process_bulk_action.delay(action.id)
#             # Start background task in a separate thread
#             background_task = threading.Thread(target=self.process_bulk_action, args=(bulk_action.id,))
#             background_task.start()
            
#             return JsonResponse({
#                 "message": "Bulk action is being processed.",
#                 "action_id": bulk_action.id
#             }, status=status.HTTP_202_ACCEPTED)
#         except Exception as e:
#             return JsonResponse({
#                 "error": "An error occurred while initiating the bulk action.",
#                 "details": str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#     @staticmethod
#     def process_bulk_action(action_id):
#         """
#         Process the bulk action by reading from the uploaded CSV file.
#         """
#         action = BulkAction.objects.get(id=action_id)

#         # Mark the action as processing
#         action.status = "PROCESSING"
#         action.started_at = timezone.now()
#         action.save()

#         try:
#             # Parse the CSV file
#             if not action.csv_file:
#                 raise ValueError("CSV file is missing for this bulk action.")

#             file_path = action.csv_file.path
#             contacts_data = parse_csv(file_path)  # List of rows (dict-like objects)

#             # Extract parameters from the action
#             deduplication = action.data.get("deduplication", "email,phone")
#             listId = action.data.get("listId", "")
#             import_option = action.data.get("importOption", "create")
#             field_mappings = action.data.get("field_mappings", [])  # ["1", "2", "3", "4", "5"]

#             # Fetch predefined and custom fields
#             predefined_fields = {str(field.id): field for field in CustomField.objects.filter(is_predefined=True)}
#             custom_fields = {str(field.id): field for field in CustomField.objects.filter(user=action.user, is_predefined=False)}

#             # Combine predefined and custom fields into a single dictionary
#             all_fields = {**predefined_fields, **custom_fields}

#             with transaction.atomic():
#                 for row in contacts_data:
#                     # Prepare a dictionary for contact creation
#                     contact_data = {}
#                     dynamic_field_data = {}

#                     for field_mapping in field_mappings:
#                         # Extract field_id from the dictionary
#                         field_id = str(field_mapping['field_id'])  # Ensure it's a string
#                         csv_header = field_mapping['csv_header']  # For debugging

#                         print(f"Processing Field ID: {field_mapping}")  # Debugging field_mapping
#                         print(f"Extracted Field ID: {field_id}, CSV Header: {csv_header}")  # Debugging extracted data

#                         # Lookup in all_fields
#                         mapped_field = all_fields.get(field_id)
#                         print("Mapped Field:", mapped_field)  # Debugging mapped_field

#                         if mapped_field:
#                             # Process mapped_field (predefined or custom)
#                             if mapped_field.is_predefined:
#                                 contact_data[mapped_field.unique_key] = row.get(csv_header, "").strip()
#                             else:
#                                 dynamic_field_data[mapped_field.unique_key] = row.get(csv_header, "").strip()
#                         else:
#                             print(f"Field ID {field_id} not found in all_fields! Skipping.")

#                     print('contact_data',contact_data)
#                     # Extract predefined fields
#                     first_name = contact_data.get("first_name", "")
#                     last_name = contact_data.get("last_name", "")
#                     email = contact_data.get("email", "")
#                     phone_number = contact_data.get("phone_number", "")
#                     contact_type = contact_data.get("contact_type", "")

#                     # Handle deduplication
#                     existing_contacts = deduplicate_contacts({"email": email, "phone": phone_number}, deduplication)
#                     print('existing_contacts',existing_contacts)
#                     if existing_contacts.exists():
#                         if import_option in ("update", "create_update"):
#                             contact = existing_contacts.first()
#                             contact.first_name = first_name
#                             contact.last_name = last_name
#                             contact.contact_type = contact_type
#                             contact.custom_fields.update(dynamic_field_data)  # Merge new custom fields
#                             contact.save()
#                     else:
#                         # Create a new contact
#                         contact = Contact.objects.create(
#                             user=action.user,
#                             first_name=first_name,
#                             last_name=last_name,
#                             contact_type=contact_type,
#                             custom_fields=dynamic_field_data,  # Save custom fields as JSON
#                         )

#                         # Add primary email
#                         if email:
#                             Email.objects.create(contact=contact, email=email, user=action.user, is_primary=True)

#                         # Add primary phone number
#                         if phone_number:
#                             PhoneNumber.objects.create(contact=contact, phone_number=phone_number, user=action.user, is_primary=True)
#                     list_obj = get_object_or_404(List, id=listId)
#                     list_obj.contacts.add(contact)  # Add the contact to the list
#             # Mark the action as completed
#             action.status = "COMPLETED"
#             action.completed_at = timezone.now()
#             action.save()

#         except Exception as e:
#             # Rollback is automatic due to transaction.atomic
#             action.status = "FAILED"
#             action.error_message = str(e)
#             action.completed_at = timezone.now()
#             action.save()
#             raise e

class BulkActionTriggerView(View):
    async def post(self, request):
        user = request.user  # Assume user is authenticated
        csv_file = request.FILES.get('csvFile')
        field_mappings = request.POST.get('fieldMappings')
        import_option = request.POST.get('importOption')
        deduplication = request.POST.get('deduplication')
        listId = request.POST.get('listId')

        if not csv_file or not field_mappings or not import_option or not deduplication:
            return JsonResponse({'error': 'Missing required data'}, status=400)

        # Parse field mappings
        try:
            field_mappings = json.loads(field_mappings)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid fieldMappings format. Must be a valid JSON string.'}, status=400)

        try:
            # Save the bulk action in the database
            with transaction.atomic():
                bulk_action = BulkAction.objects.create(
                    user=user,
                    action_type='IMPORT',
                    csv_file=csv_file,
                    data={
                        'field_mappings': field_mappings,
                        'importOption': import_option,
                        'deduplication': deduplication,
                        'listId': listId
                    },
                )

            # Trigger background task asynchronously
            asyncio.create_task(self.process_bulk_action(bulk_action.id))

            return JsonResponse({
                "message": "Bulk action is being processed.",
                "action_id": bulk_action.id
            }, status=202)  # HTTP 202 Accepted
        except Exception as e:
            return JsonResponse({
                "error": "An error occurred while initiating the bulk action.",
                "details": str(e)
            }, status=500)

    @staticmethod
    async def process_bulk_action(action_id):
        """
        Process the bulk action by reading from the uploaded CSV file.
        """
        action = BulkAction.objects.get(id=action_id)

        # Mark the action as processing
        action.status = "PROCESSING"
        action.started_at = timezone.now()
        action.save()

        try:
            # Parse the CSV file
            if not action.csv_file:
                raise ValueError("CSV file is missing for this bulk action.")

            file_path = action.csv_file.path
            contacts_data = parse_csv(file_path)  # List of rows (dict-like objects)

            # Extract parameters from the action
            deduplication = action.data.get("deduplication", "email,phone")
            listId = action.data.get("listId", "")
            import_option = action.data.get("importOption", "create")
            field_mappings = action.data.get("field_mappings", [])  # ["1", "2", "3", "4", "5"]

            # Fetch predefined and custom fields
            predefined_fields = {str(field.id): field for field in CustomField.objects.filter(is_predefined=True)}
            custom_fields = {str(field.id): field for field in CustomField.objects.filter(user=action.user, is_predefined=False)}

            # Combine predefined and custom fields into a single dictionary
            all_fields = {**predefined_fields, **custom_fields}

            async with transaction.atomic():
                for row in contacts_data:
                    # Prepare a dictionary for contact creation
                    contact_data = {}
                    dynamic_field_data = {}

                    for field_mapping in field_mappings:
                        # Extract field_id from the dictionary
                        field_id = str(field_mapping['field_id'])  # Ensure it's a string
                        csv_header = field_mapping['csv_header']  # For debugging

                        print(f"Processing Field ID: {field_mapping}")  # Debugging field_mapping
                        print(f"Extracted Field ID: {field_id}, CSV Header: {csv_header}")  # Debugging extracted data

                        # Lookup in all_fields
                        mapped_field = all_fields.get(field_id)
                        print("Mapped Field:", mapped_field)  # Debugging mapped_field

                        if mapped_field:
                            # Process mapped_field (predefined or custom)
                            if mapped_field.is_predefined:
                                contact_data[mapped_field.unique_key] = row.get(csv_header, "").strip()
                            else:
                                dynamic_field_data[mapped_field.unique_key] = row.get(csv_header, "").strip()
                        else:
                            print(f"Field ID {field_id} not found in all_fields! Skipping.")

                    print('contact_data', contact_data)
                    # Extract predefined fields
                    first_name = contact_data.get("first_name", "")
                    last_name = contact_data.get("last_name", "")
                    email = contact_data.get("email", "")
                    phone_number = contact_data.get("phone_number", "")
                    contact_type = contact_data.get("contact_type", "")

                    # Handle deduplication
                    existing_contacts = deduplicate_contacts({"email": email, "phone": phone_number}, deduplication)
                    print('existing_contacts', existing_contacts)
                    if existing_contacts.exists():
                        if import_option in ("update", "create_update"):
                            contact = existing_contacts.first()
                            contact.first_name = first_name
                            contact.last_name = last_name
                            contact.contact_type = contact_type
                            contact.custom_fields.update(dynamic_field_data)  # Merge new custom fields
                            await contact.save()
                    else:
                        # Create a new contact
                        contact = await Contact.objects.acreate(
                            user=action.user,
                            first_name=first_name,
                            last_name=last_name,
                            contact_type=contact_type,
                            custom_fields=dynamic_field_data,  # Save custom fields as JSON
                        )

                        # Add primary email
                        if email:
                            await Email.objects.acreate(contact=contact, email=email, user=action.user, is_primary=True)

                        # Add primary phone number
                        if phone_number:
                            await PhoneNumber.objects.acreate(contact=contact, phone_number=phone_number, user=action.user, is_primary=True)

                    list_obj = await get_object_or_404(List, id=listId)
                    await list_obj.contacts.aadd(contact)  # Add the contact to the list

            # Mark the action as completed
            action.status = "COMPLETED"
            action.completed_at = timezone.now()
            await action.save()

        except Exception as e:
            # Rollback is automatic due to transaction.atomic
            action.status = "FAILED"
            action.error_message = str(e)
            action.completed_at = timezone.now()
            await action.save()
            raise e

def create_contact(contact_data):
    # Create a new Contact record
    contact = Contact.objects.create(
        first_name=contact_data.get('first_name'),
        last_name=contact_data.get('last_name'),
        contact_type=contact_data.get('contact_type'),
        time_zone=contact_data.get('time_zone'),
        custom_fields=contact_data.get('custom_fields', {}),
        user=contact_data.get('user'),
    )

    # Add emails and phone numbers if provided in the data
    if 'email' in contact_data:
        email_data = contact_data.get('email')
        Email.objects.create(contact=contact, email=email_data, is_primary=True, user=contact.user)

    if 'phone_number' in contact_data:
        phone_data = contact_data.get('phone_number')
        PhoneNumber.objects.create(contact=contact, phone_number=phone_data, is_primary=True, user=contact.user)

def update_contact(contact, contact_data):
    # Update the Contact record
    contact.first_name = contact_data.get('first_name', contact.first_name)
    contact.last_name = contact_data.get('last_name', contact.last_name)
    contact.contact_type = contact_data.get('contact_type', contact.contact_type)
    contact.time_zone = contact_data.get('time_zone', contact.time_zone)
    contact.custom_fields = contact_data.get('custom_fields', contact.custom_fields)
    contact.save()

    # Update emails if new emails are provided
    if 'email' in contact_data:
        email_data = contact_data.get('email')
        email, created = Email.objects.update_or_create(
            contact=contact, 
            email=email_data,
            defaults={'is_primary': True, 'user': contact.user}
        )

    # Update phone numbers if new phone numbers are provided
    if 'phone_number' in contact_data:
        phone_data = contact_data.get('phone_number')
        phone, created = PhoneNumber.objects.update_or_create(
            contact=contact,
            phone_number=phone_data,
            defaults={'is_primary': True, 'user': contact.user}
        )

def deduplicate_contacts(contact_data, deduplication_option):
    """
    Deduplicate contacts based on the given deduplication option.
    
    :param contact_data: Dictionary with the contact's data to check.
    :param deduplication_option: String indicating deduplication strategy ('email,phone' or 'phone,email').
    :return: A QuerySet of existing contacts to avoid duplicates.
    """
    if deduplication_option == 'email,phone':
        # Check first by email, then by phone number
        existing_contacts = Contact.objects.filter(
            Q(emails__email=contact_data.get('email')) | Q(phone_numbers__phone_number=contact_data.get('phone_number'))
        )
    elif deduplication_option == 'phone,email':
        # Check first by phone number, then by email
        existing_contacts = Contact.objects.filter(
            Q(phone_numbers__phone_number=contact_data.get('phone_number')) | Q(emails__email=contact_data.get('email'))
        )
    else:
        existing_contacts = Contact.objects.none()  # No deduplication if criteria are incorrect
    
    return existing_contacts

# def deduplicate_contacts(contact_data, deduplication_fields):
#     print('deduplicate_contacts',contact_data)
#     print('deduplication_fields',deduplication_fields)
#     filters = {field: contact_data.get(field) for field in deduplication_fields if contact_data.get(field)}
#     return Contact.objects.filter(**filters)

class BulkActionStatusView(View):
    def get(self, request, action_id):
        # Fetch the action from the database
        action = BulkAction.objects.get(id=action_id,user=request.user)
        
        if action.status == 'COMPLETED':
            return JsonResponse({
                "message": "Bulk action completed successfully.",
                "status": action.status,
                "completed_at": action.completed_at
            }, status=status.HTTP_200_OK)
        
        elif action.status == 'FAILED':
            return JsonResponse({
                "message": "Bulk action failed.",
                "status": action.status,
                "error_message": action.error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # If the task is still processing
        return JsonResponse({
            "message": "Bulk action is still processing.",
            "status": action.status
        }, status=status.HTTP_202_ACCEPTED)
    
@method_decorator(csrf_exempt, name='dispatch')
class NoteAPI(View):

    def get(self, request, contact_id,note_id=None):
        if note_id:
            note = get_object_or_404(Note, id=note_id)
            data = {
                'id': note.id,
                'content': note.content,
                'contact': note.contact.id,
                'created_by': note.created_by.username,
                'created_at': note.created_at,
                'updated_at': note.updated_at
            }
        else:
            notes = Note.objects.filter(contact_id=contact_id)
            data = [
                {
                    'id': note.id,
                    'content': note.content,
                    'contact': note.contact.id,
                    'created_by': note.created_by.username,
                    'created_at': note.created_at,
                    'updated_at': note.updated_at
                } for note in notes
            ]
        return JsonResponse({'notes': data}, safe=False)

    def post(self, request,contact_id):
        try:
            body = json.loads(request.body)
            contact = get_object_or_404(Contact, id=contact_id)
            note = Note.objects.create(
                content=body['content'],
                contact=contact,
                created_by=request.user
            )
            return JsonResponse({'id': note.id, 'message': 'Note created successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def put(self, request, contact_id,note_id):
        try:
            note = get_object_or_404(Note, id=note_id,contact_id=contact_id)
            body = json.loads(request.body)
            note.content = body.get('content', note.content)
            note.save()
            return JsonResponse({'message': 'Note updated successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def delete(self, request, contact_id,note_id):
        try:
            note = get_object_or_404(Note, id=note_id,contact_id=contact_id)
            note.delete()
            return JsonResponse({'message': 'Note deleted successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
