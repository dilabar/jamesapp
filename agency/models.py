from django.db import models
from django.contrib.auth.models import User
import pytz

# Define the Agency model
class Agency(models.Model):
    name = models.CharField(max_length=100)
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # The agency is linked to a user (administrator)

    def __str__(self):
        return self.name

# Define the Client/Subaccount model
class Subaccount(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="subaccounts")
    name = models.CharField(max_length=100)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

        # General Info Fields
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Assuming phone number in E.164 format
    # Timezone validation using choices
    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.all_timezones]
    timezone = models.CharField(
        max_length=100, 
        choices=TIMEZONE_CHOICES, 
        blank=True, 
        null=True
    )


    def __str__(self):
        return self.name

# Define Role and Permissions (could use Django's built-in Groups and Permissions, but let's define custom ones for flexibility)
class Role(models.Model):
    name = models.CharField(max_length=50)
    permissions = models.TextField()  # JSON or text-based permissions (e.g., "view_data", "edit_data")

    def __str__(self):
        return self.name

# Define the Configuration model (CRM, Automations, etc.)
class Configuration(models.Model):
    subaccount = models.OneToOneField(Subaccount, on_delete=models.CASCADE, related_name="configuration")
    crm_enabled = models.BooleanField(default=True)
    automation_enabled = models.BooleanField(default=True)
    custom_data = models.JSONField(default=dict)  # Store custom settings per client

    def __str__(self):
        return f"Configuration for {self.subaccount.name}"
