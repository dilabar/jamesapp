
from django import forms

from agent.models import Agent

from .models import *
from django.utils.timezone import now

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
    lists = forms.ModelMultipleChoiceField(
        queryset=List.objects.none(),  # Updated to avoid queryset issues before user is assigned
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Lists"
    )
    individual_contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Individual Contacts"
    )
    
    campaign_type = forms.ChoiceField(
        choices=Campaign.CAMPAIGN_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select btn-pill'}),
        required=True,
        label="Campaign Type"
    )

    agent = forms.ModelChoiceField(
        queryset=Agent.objects.none(),  # Set to none initially to filter by user later
        widget=forms.Select(attrs={'class': 'form-select btn-pill'}),
        required=False,
        label="Assign Agent"
    )

    class Meta:
        model = Campaign
        fields = ['name', 'scheduled_at', 'campaign_type', 'agent', 'lists', 'individual_contacts']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control btn-pill', 'placeholder': 'Campaign Name'}),
            # 'subject': forms.TextInput(attrs={'class': 'form-control btn-pill', 'placeholder': 'Campaign Subject'}),
            # 'content': forms.Textarea(attrs={'class': 'form-control btn-pill', 'placeholder': 'Write your content here...'}),
            # 'status': forms.Select(attrs={'class': 'form-control btn-pill'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'form-control btn-pill', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Get the user from kwargs
        super().__init__(*args, **kwargs)

        if user:
            self.fields['lists'].queryset = List.objects.filter(user=user)
            self.fields['individual_contacts'].queryset = Contact.objects.filter(user=user)
            self.fields['agent'].queryset = Agent.objects.filter(user=user)  # Ensure agents are filtered by user
        self.fields['agent'].label_from_instance = lambda obj: obj.display_name  # Assuming Agent model has a 'name' field
    def clean_scheduled_at(self):
        scheduled_date = self.cleaned_data.get('scheduled_at')
        if scheduled_date and scheduled_date < now():
            raise forms.ValidationError("Scheduled date cannot be in the past.")
        return scheduled_date
    def save(self, commit=True):
        campaign = super().save(commit=False)

        # If scheduled_at is valid and in the future, update status to "Scheduled"
        if campaign.scheduled_at and campaign.scheduled_at >= now():
            campaign.status = 'scheduled'  # Ensure this matches your STATUS_CHOICES
        
        if commit:
            campaign.save()
            self.save_m2m()  # Save ManyToMany fields
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



