
from django import forms

from .models import *

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
        queryset=List.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Lists"
    )
    individual_contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Individual Contacts"
    )

    class Meta:
        model = Campaign
        fields = ['name', 'subject', 'content', 'status', 'scheduled_at', 'lists', 'individual_contacts']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Campaign Name'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Campaign Subject'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write your content here...'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['lists'].queryset = List.objects.filter(user=user)
            self.fields['individual_contacts'].queryset = Contact.objects.filter(user=user)



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
