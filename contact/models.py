from django.db import models

from agency.models import User

# Create your models here.


class Contact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact',null=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    contact_type = models.CharField(max_length=50, choices=[('Customer', 'Customer'), ('Vendor', 'Vendor')])
    time_zone = models.CharField(max_length=50, blank=True, null=True)
    custom_fields = models.JSONField(default=dict, blank=True)  # Store additional fields as JSON.
    last_activity = models.DateTimeField(blank=True, null=True)
    # Removed dnd_preferences for now
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}"
    




class Email(models.Model):
    contact = models.ForeignKey(Contact, related_name='emails', on_delete=models.CASCADE)
    email = models.EmailField()
    is_primary = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emails")

    class Meta:
        unique_together = ('user', 'email')  # Ensure email is unique per user.

    def __str__(self):
        return self.email

class PhoneNumber(models.Model):
    contact = models.ForeignKey(Contact, related_name='phone_numbers', on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    country_code = models.CharField(max_length=15, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="phone_numbers")

    class Meta:
        unique_together = ('user', 'phone_number')  # Ensure phone number is unique per user.

    def __str__(self):
        return self.phone_number




# List Model (Group Contacts)
class List(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lists',null=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    contacts = models.ManyToManyField(Contact, related_name='lists', through='ListContact')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ListContact Model (Tracks Contact Subscription to a List)
class ListContact(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    list = models.ForeignKey(List, on_delete=models.CASCADE)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    # class Meta:
    #     unique_together = ('contact', 'list')


# Campaign Model
class Campaign(models.Model):
    RECURRING = 'recurring'
    ONE_TIME = 'one_time'

    CAMPAIGN_TYPE_CHOICES = [
        (RECURRING, 'Recurring'),
        (ONE_TIME, 'One-time'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns', null=True)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('started', 'Started'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
        ('paushed', 'Paushed'),
    ]
    campaign_type = models.CharField(
        max_length=20, choices=CAMPAIGN_TYPE_CHOICES, default=ONE_TIME
    )
    name = models.CharField(max_length=255, unique=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    lists = models.ManyToManyField(List, related_name='campaigns', blank=True)
    individual_contacts = models.ManyToManyField(Contact, related_name='campaigns', blank=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    triggers = models.JSONField(default=dict, blank=True)  # Store automation triggers.
    agent = models.ForeignKey('agent.Agent', on_delete=models.CASCADE,related_name='campaigns', null=True, blank=True)


    def __str__(self):
        return self.name

    def get_recipients(self):
        """Get all contacts targeted by this campaign."""
        contacts_from_lists = Contact.objects.filter(lists__in=self.lists.all()).distinct()
        direct_contacts = self.individual_contacts.all()
        return contacts_from_lists.union(direct_contacts)
    def is_recurring(self):
        """Returns True if the campaign is recurring."""
        return self.campaign_type == self.RECURRING

    def is_one_time(self):
        """Returns True if the campaign is one-time."""
        return self.campaign_type == self.ONE_TIME


class CustomField(models.Model):
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('select', 'Select'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="custom_fields")
    name = models.CharField(max_length=100)  # Field name
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')  # Type of the field
    options = models.JSONField(blank=True, null=True)  # For select fields, store options as JSON
    is_predefined=models.BooleanField(blank=True,null=True,default=False)
    unique_key = models.CharField(max_length=255, unique=True, null=False, blank=False) 
    # unique_key = models.CharField(max_length=255, null=True, blank=True)  # Allow null initially
    def __str__(self):
        return self.name


class BulkAction(models.Model):
    ACTION_TYPES = [
        ('IMPORT', 'Import'),
        ('EXPORT', 'Export'),
        ('DELETE', 'Delete'),
        # add more types as needed
    ]
    
    status_choices = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='bulk_actions'
    )  # Associate the bulk action with a user
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    status = models.CharField(max_length=20, choices=status_choices, default='PENDING')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)  # For storing error messages if any
    data = models.JSONField(default=dict)  # Store data required for the action
    created_at = models.DateTimeField(auto_now_add=True)
    csv_file = models.FileField(upload_to='bulk_uploads/', null=True, blank=True)

    def __str__(self):
        return f"{self.action_type} - {self.status}"
class Note(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='notes')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")


    def __str__(self):
        return f"{self.content}"
    

class RevokedTask(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    revoked_at = models.DateTimeField(auto_now_add=True)  # Track when revoked

    def __str__(self):
        return self.task_id