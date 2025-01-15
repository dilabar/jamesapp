# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import SubAccountProfile, User
import pytz

class SubaccountForm(UserCreationForm):
    # Additional fields from SubAccountProfile
    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.all_timezones]
    phone_number = forms.CharField(
        max_length=15, 
        required=False, 
        help_text="Phone number of the sub-account"
    )
    address = forms.CharField(
        widget=forms.Textarea, 
        required=False, 
        help_text="Address of the sub-account"
    )
    city = forms.CharField(
        max_length=100, 
        required=False, 
        help_text="City of the sub-account"
    )
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES, 
        required=False, 
        help_text="Timezone of the sub-account"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']  # Include first_name and last_name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom CSS classes and placeholders for each field
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Subaccount Username'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Email Address'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter First Name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Last Name'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
        self.fields['phone_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Phone Number'
        })
        self.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter Address'
        })
        self.fields['city'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter City'
        })
        self.fields['timezone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Select Timezone'
        })

    def save(self, commit=True, parent_agency=None):
        # Save the user instance
        user = super().save(commit=False)
        user.user_type = 'sub_account'
        user.parent_agency = parent_agency
        if commit:
            user.save()
            # Create and save the associated SubAccountProfile
            SubAccountProfile.objects.create(
                sub_account=user,
                phone_number=self.cleaned_data.get('phone_number'),
                address=self.cleaned_data.get('address'),
                city=self.cleaned_data.get('city'),
                timezone=self.cleaned_data.get('timezone'),
            )
        return user
# Form to configure a subaccount's settings
# class ConfigurationForm(forms.ModelForm):
#     class Meta:
#         model = Configuration
#         fields = ['crm_enabled', 'automation_enabled', 'user_limit']
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
        
#         # Add custom CSS classes and placeholders for each field
#         self.fields['crm_enabled'].widget.attrs.update({
#             'class': 'form-check-input',
#         })
#         self.fields['automation_enabled'].widget.attrs.update({
#             'class': 'form-check-input',
#         })
#         self.fields['user_limit'].widget.attrs.update({
#             'class': 'form-control',
#             'placeholder': 'Enter User limit'
#         })
      