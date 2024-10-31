from django.db import models

from jamesapp import settings
from jamesapp.utils import decrypt, encrypt

# Create your models here.
class Agent(models.Model):
    id = models.AutoField(primary_key=True)  # Auto-incrementing primary key
    agent_id = models.CharField(max_length=255, unique=True)  # Unique agent ID from Play.ai
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set at creation
    updated_at = models.DateTimeField(auto_now=True)      # Automatically update on save
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agents',null=True)

    def save(self, *args, **kwargs):
        # Encrypt sensitive data before saving
        if self.agent_id:
            self.agent_id = encrypt(self.agent_id)
        super().save(*args, **kwargs)
    @property
    def decrypted_agent_id(self):
        return decrypt(self.agent_id)
    
    def __str__(self):
        return self.name

    
class PhoneCall(models.Model):
    phone_number = models.CharField(max_length=20)
    call_status = models.CharField(max_length=20)
    twilio_call_id = models.CharField(max_length=100,null=True)
    feedback = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class ServiceDetail(models.Model):
    SERVICE_CHOICES = [
        ('play_ai', 'Play.ai'),
        ('twilio', 'Twilio'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='services',null=True)
    service_name = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    account_sid = models.CharField(max_length=255, blank=True, null=True)
    twilio_phone = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'service_name')  # Ensures each user can only have one instance per service

 
    def save(self, *args, **kwargs):
        # Encrypt sensitive data before saving
        if self.api_key:
            self.api_key = encrypt(self.api_key)
        if self.twilio_phone:
            self.twilio_phone = encrypt(self.twilio_phone)
        if self.account_sid:
            self.account_sid = encrypt(self.account_sid)
        super().save(*args, **kwargs)
        
    @property
    def decrypted_api_key(self):
        return decrypt(self.api_key)

    @property
    def decrypted_twilio_phone(self):
        return decrypt(self.twilio_phone)

    @property
    def decrypted_account_sid(self):
        return decrypt(self.account_sid)

    def __str__(self):
        return f"{self.service_name}"