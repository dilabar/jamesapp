import csv
import os
import requests
import chardet
from contact.models import Contact, Email, PhoneNumber
from cryptography.fernet import Fernet
from django.conf import settings
from base64 import urlsafe_b64encode, urlsafe_b64decode
from django.db import transaction
from django.db.models import Q 


# Generate a key (Only do this once, then store it securely!)
# key = Fernet.generate_key()

# Retrieve the key from an environment variable or settings
ENCRYPTION_KEY = "2R2b2TIyweYG3T9KG7K2sXlgcNXCAEUsU0m0-Zp8a50="  # For example, using the first 32 bytes of Django's SECRET_KEY
# cipher = Fernet(urlsafe_b64encode(ENCRYPTION_KEY.encode()))
cipher = Fernet(ENCRYPTION_KEY)

def encrypt(value):
    if value:
        return cipher.encrypt(value.encode()).decode()
    return None

def decrypt(value):
    if value:
        return cipher.decrypt(value.encode()).decode()
    return None
def get_conversation_data(agent_id,PLAY_AI_API_KEY,PLAY_AI_USER_ID):
    """
    Utility function to fetch data from the Play AI API.

    Parameters:
    - agent_id (str): The unique identifier for the agent.

    Returns:
    - dict: Response data from Play AI or an error message.
    """
    api_url = f"https://api.play.ai/api/v1/agents/{agent_id}/conversations" # Adjust endpoint URL based on Play AI's API documentation
    querystring = {"pageSize":"50","startAfter":"0"}
    headers = {
        "Authorization": f"Bearer {PLAY_AI_API_KEY}",
        "X-USER-ID": PLAY_AI_USER_ID,
        "Accept": "application/json"
    }


    try:
        response = requests.get(api_url, headers=headers,params=querystring)
        response.raise_for_status()  # Will raise an HTTPError for non-2xx responses
        return response.json()  # Parse and return the JSON response data

    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}"}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request error occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}
    
def get_transcript_data(agent_id,cid,PLAY_AI_API_KEY,PLAY_AI_USER_ID,pagesize=10,startafter=0):
    """
    Utility function to fetch data from the Play AI API.

    Parameters:
    - agent_id (str): The unique identifier for the agent.

    Returns:
    - dict: Response data from Play AI or an error message.
    """
    api_url = f"https://api.play.ai/api/v1/agents/{agent_id}/conversations/{cid}/transcript" # Adjust endpoint URL based on Play AI's API documentation
    querystring = {"pageSize":pagesize,"startAfter":startafter}
    headers = {
        "Authorization": f"Bearer {PLAY_AI_API_KEY}",
        "X-USER-ID": PLAY_AI_USER_ID,
        "Accept": "application/json"
    }


    try:
        response = requests.get(api_url, headers=headers,params=querystring)
        response.raise_for_status()  # Will raise an HTTPError for non-2xx responses
        return response.json()  # Parse and return the JSON response data

    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}"}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request error occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}
    
def fetch_data_from_api(url, headers, params=None):
    """
    Helper function to make GET requests to an API endpoint.

    Parameters:
    - url (str): The API URL endpoint.
    - headers (dict): Headers to include in the request.
    - params (dict, optional): URL parameters for the request.

    Returns:
    - dict: The JSON response from the API or an error message.
    """
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        return {"error": f"HTTP error occurred: {http_err}"}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Request error occurred: {req_err}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}
    

    """
    Initiates a call using Twilio and creates a PhoneCall record.

    Parameters:
        request (HttpRequest): The HTTP request object to access scheme and host.
        phone_number (str): The phone number to call.
        user (User): The logged-in user who initiated the campaign.
        agnt_id (int): The ID of the agent initiating the call.
        campaign (Campaign): The campaign associated with the call.
        client (Client): The Twilio client instance.
        twilio_phone (str): The Twilio phone number to use for making calls.
    
    Returns:
        bool: True if the call was initiated successfully, False if failed.
    """
    try:
        PhoneCall = apps.get_model('contact', 'PhoneCall')  # Lazy load model dynamically
        # Create PhoneCall record
        phone_call = PhoneCall.objects.create(
            phone_number=phone_number,
            call_status='pending',
            user=user,
            agnt_id=agnt_id,
            campaign=campaign
        )

        # Initiate the call via Twilio
        call = client.calls.create(
            url=f'{request.scheme}://{request.get_host()}/call/start_twilio_stream/{user.id}/{agnt_id}/',
            to=phone_call.phone_number,
            from_=twilio_phone,
            record=True,
            method='POST',
            status_callback=f'{request.scheme}://{request.get_host()}/call/call_status_callback/{phone_call.id}/',
            status_callback_method='POST',
            status_callback_event=["initiated", "ringing", "answered", "completed"]
        )

        # Update the call status and save it
        phone_call.call_status = 'initiated'
        phone_call.twilio_call_id = call.sid
        phone_call.save()

        return True  # Return True if the call was initiated successfully

    except Exception as e:
        phone_call.call_status = 'failed'
        phone_call.save()
        
        return False  # Return False if there was an error
    
    
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
    print(contact_data.get('email'))
    print(contact_data.get('phone_number'))
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
