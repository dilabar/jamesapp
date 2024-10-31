import os
from cryptography.fernet import Fernet
from django.conf import settings
from base64 import urlsafe_b64encode, urlsafe_b64decode

# Generate a key (Only do this once, then store it securely!)
# key = Fernet.generate_key()

# Retrieve the key from an environment variable or settings
ENCRYPTION_KEY = settings.SECRET_KEY[:32]  # For example, using the first 32 bytes of Django's SECRET_KEY
cipher = Fernet(urlsafe_b64encode(ENCRYPTION_KEY.encode()))

def encrypt(value):
    if value:
        return cipher.encrypt(value.encode()).decode()
    return None

def decrypt(value):
    if value:
        return cipher.decrypt(value.encode()).decode()
    return None
