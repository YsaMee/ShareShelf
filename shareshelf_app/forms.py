import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import PROGRAM_CHOICES

class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'you@school.edu'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )

class SignUpForm(forms.Form):
    name = forms.CharField(max_length=80, widget=forms.TextInput(attrs={'placeholder': 'Your full name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'you@students.mcm.edu.ph'}))
    program = forms.ChoiceField(choices=PROGRAM_CHOICES)
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))
    agree = forms.BooleanField(required=True, error_messages={'required': 'You must agree to the Terms of Service and Privacy Policy.'})

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        if not email.endswith('.edu.ph'):
            raise ValidationError("Must be a school address ending in .edu.ph")
        if User.objects.filter(username=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            raise ValidationError("Password must contain both letters and digits.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data