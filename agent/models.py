from django.db import models

# Create your models here.
class Agent(models.Model):
    id = models.AutoField(primary_key=True)  # Auto-incrementing primary key
    agent_id = models.CharField(max_length=255, unique=True)  # Unique agent ID from Play.ai
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    def __str__(self):
        return self.name
    
class PhoneCall(models.Model):
    phone_number = models.CharField(max_length=20)
    call_status = models.CharField(max_length=20)
    feedback = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)