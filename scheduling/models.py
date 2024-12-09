from django.conf import settings
from django.db import models

# Create your models here.
class CalendarConnection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=50)  # e.g., 'google', 'outlook'
    credentials = models.JSONField()  # Store OAuth credentials
    created_at = models.DateTimeField(auto_now_add=True)
    is_default = models.BooleanField(default=False)  # Mark the default calendar
    
    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default calendar per user
            CalendarConnection.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

class Availability(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    day_of_week = models.CharField(max_length=10)  # e.g., 'Monday'
    created_at = models.DateTimeField(auto_now_add=True)