from datetime import timedelta
import hashlib
from django.db import models

from django.core.validators import RegexValidator
from agency.models import User
from contact.models import Campaign, Contact
from jamesapp import settings
from rateMaster.models import CallRate 
from jamesapp.utils import decrypt, encrypt

# Create your models here.
class Agent(models.Model):
    id = models.AutoField(primary_key=True)  # Auto-incrementing primary key
    agent_id = models.CharField(max_length=255, unique=True,null=True, blank=True)
    agent_id_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)  # Use SHA-256 hash
    voice = models.CharField(max_length=500, blank=True, null=True)
    voice_speed = models.FloatField(null=True, blank=True)
    display_name = models.CharField(max_length=255,null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    greeting = models.TextField(null=True, blank=True)
    prompt = models.TextField(null=True, blank=True)
    critical_knowledge = models.TextField(null=True, blank=True)
    visibility = models.CharField(max_length=50,null=True, blank=True)
    answer_only_from_critical_knowledge = models.BooleanField(null=True, blank=True)
    avatar_photo_url = models.URLField(null=True, blank=True)
    critical_knowledge_files = models.JSONField(null=True, blank=True)
    phone_numbers = models.JSONField(null=True, blank=True)  # To store list of phone numbers as JSON
    real_agent_no = models.CharField(max_length=20,null=True,blank=True)
    llm_base_url = models.URLField(null=True, blank=True)
    llm_api_key = models.CharField(max_length=255,null=True, blank=True)
    llm_model = models.CharField(max_length=255,null=True, blank=True)
    llm_temperature = models.FloatField(null=True, blank=True)
    llm_max_tokens = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)      # Automatically update on save
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agents',null=True)

    # def save(self, *args, **kwargs):
    #     # Encrypt sensitive data before saving
    #     if self.agent_id:
    #         self.agent_id_hash = hashlib.sha256(self.agent_id.encode()).hexdigest()
    #         self.agent_id = encrypt(self.agent_id)
    #     super().save(*args, **kwargs)
    @property
    def decrypted_agent_id(self):
        return decrypt(self.agent_id)
    
    def __str__(self):
        return f"{self.id}"

    
class PhoneCall(models.Model):
    phone_number = models.CharField(max_length=20)
    call_status = models.CharField(max_length=20)
    twilio_call_id = models.CharField(max_length=100,null=True)
    play_ai_conv_id = models.CharField(max_length=100,null=True)
    feedback = models.TextField(blank=True, null=True)
    is_call_forwarded=models.BooleanField(blank=True,null=True,default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
     # Play.ai-specific fields
    agent_owner_id = models.CharField(max_length=100, null=True)  # Added agentOwnerId
    agent_id = models.CharField(max_length=255, null=True)  # Added agentOwnerId
    # Use ForeignKey to connect with Agent model
    agnt = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name='phone_calls')
    recording_presigned_url = models.URLField(max_length=500, null=True)  # Added recordingPresignedUrl
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='phonecall',null=True)
    hand_off_summary=models.TextField(blank=True,null=True)
    transcription_text = models.TextField(blank=True,null=True)

    # Self-referential foreign key
    from_call_id = models.ForeignKey(
        'self',  # Referencing the same model
        on_delete=models.SET_NULL,  # Handle deletion of referenced call
        null=True,
        blank=True,
        related_name='related_calls'  # Related name for reverse lookup
    )

    # Additional metadata from callback
    recording_url = models.URLField(max_length=500, null=True)  # URL of the recording
    recording_sid = models.CharField(max_length=100, null=True)  # Recording SID
    call_duration = models.IntegerField(null=True, blank=True)  # Total call duration in seconds
    recording_duration = models.IntegerField(null=True, blank=True)  # Recording duration in seconds
    caller = models.CharField(max_length=20, null=True)  # Caller phone number
    called = models.CharField(max_length=20, null=True)  # Called phone number
    direction = models.CharField(max_length=50, null=True)  # Call direction (e.g., outbound-api)
    from_country = models.CharField(max_length=50, null=True)  # Originating country
    to_country = models.CharField(max_length=50, null=True)  # Destination country
    from_city = models.CharField(max_length=100, null=True)  # Originating city
    to_city = models.CharField(max_length=100, null=True)  # Destination city
    # Add a ForeignKey to Campaign model to associate the call with a campaign
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='phone_calls_for_campaign')
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='phone_calls_for_contact')
    
    
    

class ServiceDetail(models.Model):
    SERVICE_CHOICES = [
        ('play_ai', 'Play.ai'),
        ('twilio', 'Twilio'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services',null=True)
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
    
class GoogleCalendarEvent(models.Model):
    # Event Title
    summary = models.CharField(max_length=255)
    
    # Event Start and End Times
    start_time = models.DateTimeField(null=True,blank=True)
    end_time = models.DateTimeField(null=True,blank=True)

    # Event Description
    description = models.TextField(null=True,blank=True)

    # Attendees (storing emails of attendees)
    attendees = models.JSONField(null=True,blank=True)  # To store a list of email addresses
    
    # Google Calendar Event ID and Link
    calendar_event_id = models.CharField(max_length=255, unique=True,null=True,blank=True)
    calendar_link = models.URLField(null=True,blank=True)

    # Status of the booking
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')

    # Timestamps for when the event was created/modified
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Meeting: {self.summary} on {self.start_time}"
    




