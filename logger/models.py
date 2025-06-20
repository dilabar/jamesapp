from django.db import models

from agency.models import User

# Create your models here.
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True)  # Directly store JSON data

    def __str__(self):
        return f"Activity by {self.user} at {self.timestamp}"