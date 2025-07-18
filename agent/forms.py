from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
# from django.contrib.auth.models import User
from agency.models import AgencyAccount, User
from .models import *

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    agency_name = forms.CharField(max_length=255, required=True)
    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.fields['agency_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Agency name'})
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Email'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email
    def save(self, commit=True):
        # Save the user instance
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.user_type = 'agency'  # Set user type to 'agency'
                # Check if passwords match (handled by UserCreationForm, but we are overriding the save method)
        if self.cleaned_data.get('password1') != self.cleaned_data.get('password2'):
            raise forms.ValidationError("Passwords do not match.")

        if commit:
            user.save()
            # Create the associated AgencyAccount
            AgencyAccount.objects.create(
                agency=user,    
                agency_name=self.cleaned_data['agency_name']
            )
        return user
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))



class ServiceDetailForm(forms.ModelForm):
    # Custom fields to display decrypted values and allow encrypted input
    api_key = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter API Key'}),
        label="API Key"
    )
    account_sid = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Account SID'}),
        label="Account SID"
    )
    twilio_phone = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Twilio Phone No'}),
        label="Twilio phone"
    )

    class Meta:
        model = ServiceDetail
        fields = ['service_name', 'api_key', 'account_sid', 'twilio_phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the fields with decrypted values if the instance is provided
        self.fields['service_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['api_key'].widget.attrs.update({'class': 'form-control', 'maxlength': '255'})
        self.fields['account_sid'].widget.attrs.update({'class': 'form-control', 'maxlength': '255'})
        self.fields['twilio_phone'].widget.attrs.update({'class': 'form-control', 'maxlength': '255'})
        if self.instance.pk:
            self.fields['api_key'].initial = self.instance.decrypted_api_key
            self.fields['account_sid'].initial = self.instance.decrypted_account_sid
            self.fields['twilio_phone'].initial = self.instance.decrypted_twilio_phone

    def save(self,user=None, commit=True):
        # Override save to encrypt sensitive data before saving
        instance = super().save(commit=False)
        # Encrypt data before saving to the database
        instance.api_key = self.cleaned_data.get('api_key', '')
        instance.account_sid = self.cleaned_data.get('account_sid', '')
        instance.twilio_phone = self.cleaned_data.get('twilio_phone', '')

        if user:
            instance.user = user  # Set the user if provided
        
        if commit:
            instance.save()
        return instance
class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['agent_id', 'display_name', 'description','real_agent_no']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adding custom CSS classes for styling if needed
        self.fields['agent_id'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter Agent ID'})
        self.fields['display_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter Agent Name'})
        self.fields['real_agent_no'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter Real Agent No'})
        self.fields['description'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter Description'})
        
        if self.instance.pk:
            self.fields['agent_id'].initial = self.instance.decrypted_agent_id
            self.fields['real_agent_no'].initial = self.instance.real_agent_no


    def save(self,user=None, commit=True):
        # Override save to encrypt sensitive data before saving
        instance = super().save(commit=False)
        # Encrypt data before saving to the database
        instance.agent_id = self.cleaned_data.get('agent_id', '')
        instance.display_name = self.cleaned_data.get('display_name', '')
        instance.real_agent_no = self.cleaned_data.get('real_agent_no', '')
        instance.description = self.cleaned_data.get('description', '')

        if user:
            instance.user = user  # Set the user if provided
        
        if commit:
            instance.save()
        return instance
    

class AgentFormV1(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # ✅ request.user ko form me pass karne ke liye
        super().__init__(*args, **kwargs)
        
        self.fields["display_name"].required = True
        self.fields["greeting"].required = True

        # Optional example:
        self.fields["description"].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
       
        if self.user:
            instance.user = self.user  # ✅ request.user assign karna
        if commit:
            instance.save()
        return instance
    voice_speed = forms.ChoiceField(
        choices=[
            (0.5, "0.5"), (0.6, "0.6"), (0.7, "0.7"), (0.8, "0.8"), (0.9, "0.9"),
            (1.0, "1.0"), (1.1, "1.1"), (1.2, "1.2"), (1.3, "1.3"), (1.4, "1.4"), (1.5, "1.5")
        ],
        initial=1.0,  # ✅ Default value set
        widget=forms.Select(attrs={"class": "form-control"})
    )
    llm_model = forms.ChoiceField(
        choices=[
            ("PlayHT2.0-turbo", "PlayHT2.0-turbo"),
            ("Play3.0-mini", "Play3.0-mini"),
            ("PlayDialog", "PlayDialog"),
            ("play-tts", "play-tts")
        ],
        initial="PlayDialog",  # ✅ Default value
        widget=forms.Select(attrs={"class": "form-control"})
        )

    class Meta:
        model = Agent
        fields = [
            "voice", "voice_speed", "display_name", "description", "greeting",
            "prompt", "critical_knowledge", "visibility",
            "answer_only_from_critical_knowledge", "avatar_photo_url",
            "critical_knowledge_files", "phone_numbers", "llm_model"
        ]
      
        widgets = {
            "voice": forms.TextInput(attrs={"class": "form-control","value":"s3://voice-cloning-zero-shot/37RKAKle9paS_85btF3lr/your-voice/manifest.json"}),
            # "voice_speed": forms.Select(
            # attrs={"class": "form-control"},
            #     choices=[
            #         (0.5, "0.5"), (0.6, "0.6"), (0.7, "0.7"), (0.8, "0.8"), (0.9, "0.9"),
            #         (1.0, "1.0"), (1.1, "1.1"), (1.2, "1.2"), (1.3, "1.3"), (1.4, "1.4"), (1.5, "1.5")
            #     ]
            # ),
            "display_name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "greeting": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "prompt": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "critical_knowledge": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "visibility": forms.Select(attrs={"class": "form-control"}, choices=[("public", "Public"), ("private", "Private")]),
            "answer_only_from_critical_knowledge": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "avatar_photo_url": forms.URLInput(attrs={"class": "form-control"}),
            # "llm_model": forms.TextInput(attrs={"class": "form-control"},value="play"),
        }


