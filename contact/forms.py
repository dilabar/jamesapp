
from django import forms

from agent.models import Agent, TwilioPhoneNumber

from .models import *
from django.utils.timezone import now
from django.core.exceptions import ValidationError

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'contact_type', 'time_zone']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the fields with decrypted values if the instance is provided
        self.fields['first_name'].widget.attrs.update({'class': 'form-control input-air-primary'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control input-air-primary'})
        self.fields['contact_type'].widget.attrs.update({'class': 'form-control input-air-primary'})
        self.fields['time_zone'].widget.attrs.update({'class': 'form-control input-air-primary'})
        
    # You can customize widgets, add validation here if needed

class EmailForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control input-air-primary',
            'placeholder': 'Enter email address'
        }),
        label='Email Address',
        required=True,
    )

    class Meta:
        model = Email
        fields = ['email']

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:  # Assign the user if provided
            instance.user = user
        if commit:
            instance.save()
        return instance


class PhoneNumberForm(forms.ModelForm):
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control input-air-primary',
            'placeholder': 'Enter phone number'
        }),
        label='Phone Number',
        required=True,
    )

    class Meta:
        model = PhoneNumber
        fields = ['phone_number']

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:  # Assign the user if provided
            instance.user = user
        if commit:
            instance.save()
        return instance


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label='Upload Excel File')




# Form for the List Model
class ListForm(forms.ModelForm):
    contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = List
        fields = ['name', 'description', 'contacts']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }





class CampaignForm(forms.ModelForm):
    lists = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
        label="Target Lists"
    )
    
    individual_contacts = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        label="Individual Contacts"
    )

    campaign_type = forms.ChoiceField(
        choices=Campaign.CAMPAIGN_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select btn-pill'}),
        required=True,
        label="Campaign Type"
    )

    agent = forms.ModelChoiceField(
        queryset=Agent.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select btn-pill'}),
        required=False,
        label="Assign Agent"
    )
    twilio_phone = forms.ModelChoiceField(
        queryset=TwilioPhoneNumber.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select btn-pill'}),
        required=True,
        label="Send From (Twilio Number)"
    )
    class Meta:
        model = Campaign
        fields = ['name', 'scheduled_at', 'campaign_type', 'agent','twilio_phone', 'lists', 'individual_contacts']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control btn-pill', 'placeholder': 'Campaign Name'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'form-control btn-pill', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  
        super().__init__(*args, **kwargs)

        if user:
            self.fields['agent'].queryset = Agent.objects.filter(user=user)
            self.fields['twilio_phone'].queryset = TwilioPhoneNumber.objects.filter(service__user=user)

        self.fields['agent'].label_from_instance = lambda obj: obj.display_name.title()
        self.fields['twilio_phone'].label_from_instance = lambda obj: obj.phone_number  
        # Disable all campaign types except 'ontime'
        # campaign_type_choices = self.fields['campaign_type'].choices
     
        # self.fields['campaign_type'].choices = [choice for choice in campaign_type_choices if choice[0] == 'one_time']
        # self.fields['campaign_type'].widget.attrs['disabled'] = True  # Disable the entire select field so only 'one time' is available

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or len(name) < 3:
            raise ValidationError("Campaign name must be at least 3 characters long.")
        return name

    def clean_scheduled_at(self):
        scheduled_date = self.cleaned_data.get('scheduled_at')
        if scheduled_date and scheduled_date < now():
            raise ValidationError("Scheduled date cannot be in the past.")
        return scheduled_date

    def clean(self):
        cleaned_data = super().clean()

        lists = cleaned_data.get("lists", "").strip()  # Get lists as string
        individual_contacts = cleaned_data.get("individual_contacts", "").strip()  # Get contacts as string

        # Ensure at least one selection
        if not lists and not individual_contacts:
            raise forms.ValidationError("You must select at least one list or an individual contact.")

        # Convert comma-separated IDs to QuerySet
        lists_ids = [int(id) for id in lists.split(",") if id.isdigit()]
        individual_contacts_ids = [int(id) for id in individual_contacts.split(",") if id.isdigit()]

        cleaned_data["lists"] = List.objects.filter(id__in=lists_ids) if lists_ids else List.objects.none()
        cleaned_data["individual_contacts"] = Contact.objects.filter(id__in=individual_contacts_ids) if individual_contacts_ids else Contact.objects.none()

        return cleaned_data

    def save(self, commit=True):
        campaign = super().save(commit=False)

        # Set status based on scheduled date
        if campaign.scheduled_at and campaign.scheduled_at >= now():
            campaign.status = 'scheduled'

        if commit:
            campaign.save()
            self.save_m2m()  # Ensure many-to-many fields (lists & contacts) are saved

        return campaign
class CustomFieldForm(forms.ModelForm):
    class Meta:
        model = CustomField
        fields = ['name', 'field_type', 'options','unique_key']
        widgets = {
            'options': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Comma-separated options for select fields (e.g., Option1,Option2)'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Accept additional context (e.g., the current user) via kwargs
        self.user = kwargs.pop('user', None)  # Example of passing the current user
        super().__init__(*args, **kwargs)

        # Dynamically modify field properties
        self.fields['name'].widget.attrs.update({
            'placeholder': 'Enter the name of the custom field','class': 'form-control input-air-primary',
        })
        self.fields['field_type'].widget.attrs.update({
            'class': 'field-type-dropdown form-control input-air-primary', # Add CSS class for frontend customization
        })
        self.fields['options'].widget.attrs.update({
            'class': 'options-textarea form-control input-air-primary',
        })
        self.fields['unique_key'].widget.attrs.update({
            'class': 'form-control input-air-primary',
        })

      
        # # Optionally, filter or modify field_type choices
        # if self.user:
        #     # Example: Limit available field types for non-superusers
        #     allowed_types = ['text', 'number', 'date']  # Restrict available options
        #     self.fields['field_type'].choices = [
        #         (key, value) for key, value in self.fields['field_type'].choices if key in allowed_types
        #     ]

    def clean(self):
        cleaned_data = super().clean()
        field_type = cleaned_data.get('field_type')
        options = cleaned_data.get('options')
        unique_key = cleaned_data.get('unique_key')

        print(options)
        # Validate options for select fields
        if field_type == 'select' and not options:
            raise forms.ValidationError("Options are required for select fields.")
        if options:
            # Ensure options are stored as a JSON array
            cleaned_data['options'] = [opt.strip() for opt in options.split(',') if opt.strip()]
            print(cleaned_data)
        return cleaned_data



