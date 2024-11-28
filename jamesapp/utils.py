import os
import requests
from cryptography.fernet import Fernet
from django.conf import settings
from base64 import urlsafe_b64encode, urlsafe_b64decode

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
    
