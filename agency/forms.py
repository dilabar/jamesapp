# forms.py
from django import forms
from .models import Configuration, Subaccount
import pytz

class SubaccountForm(forms.ModelForm):
    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.all_timezones]

    class Meta:
        model = Subaccount
        fields = ['name', 'email', 'address', 'city', 'phone_number', 'timezone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom CSS classes and placeholders for each field
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Subaccount Name'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Email Address'
        })
        self.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Address'
        })
        self.fields['city'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter City'
        })
        self.fields['phone_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Phone Number'
        })
        self.fields['timezone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Select Timezone'
        })


# Form to configure a subaccount's settings
class ConfigurationForm(forms.ModelForm):
    class Meta:
        model = Configuration
        fields = ['crm_enabled', 'automation_enabled', 'user_limit']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom CSS classes and placeholders for each field
        self.fields['crm_enabled'].widget.attrs.update({
            'class': 'form-check-input',
        })
        self.fields['automation_enabled'].widget.attrs.update({
            'class': 'form-check-input',
        })
        self.fields['user_limit'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter User limit'
        })
      