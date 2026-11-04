import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from .models import Item, PROGRAM_CHOICES, Request, UserProfile, LOCATION_CHOICES, YEAR_LEVEL_CHOICES

class LoginForm(forms.Form):
    email = forms.EmailField(
         widget=forms.EmailInput(attrs={'placeholder': 'you@school.edu'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )

def min_length(n):
    return lambda password: len(password) >= n

def contains(pattern):
    return lambda password: re.search(pattern, password) is not None

def all_of(*checks):
    return lambda password: all(check(password) for check in checks)

PASSWORD_RULES = (
    (min_length(8), "Password must be at least 8 characters long."),
    (all_of(contains(r'[A-Za-z]'), contains(r'\d')), "Password must contain both letters and digits."),
)

def password_rule_errors(password):
    broken = filter(lambda rule: not rule[0](password or ''), PASSWORD_RULES)
    return list(map(lambda rule: rule[1], broken))

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


class ShareItemForm(forms.ModelForm):
    """OOP form: validates item input against the Item model."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('initial', {'listing': 'give', 'condition': 'Gently Used', 'qty': 1})
        super().__init__(*args, **kwargs)

    class Meta:
        model = Item
        fields = ('listing', 'name', 'qty', 'category', 'condition', 'lend_limit', 'location', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. TI-84 Plus CE Graphing Calculator'}),
            'qty': forms.NumberInput(attrs={'min': 1, 'max': 20}),
            'description': forms.Textarea(attrs={'rows': 3, 'maxlength': 500}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('listing') == 'lend' and not cleaned.get('lend_limit'):
            self.add_error('lend_limit', 'Choose a maximum lending duration.')
        if cleaned.get('listing') == 'give':
            cleaned['lend_limit'] = None
        return cleaned


class RequestPostForm(forms.ModelForm):
    """OOP form for posting an item request."""

    needed_by = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    location = forms.ChoiceField(choices=Item.LOCATION_CHOICES)

    class Meta:
        model = Request
        fields = ('name', 'category', 'preference', 'note', 'needed_by', 'location')
        widgets = {
            'name': forms.TextInput(attrs={'maxlength': 80}),
            'note': forms.Textarea(attrs={'rows': 3, 'maxlength': 200}),
            'needed_by': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_needed_by(self):
        needed_by = self.cleaned_data['needed_by']
        from django.utils import timezone
        if needed_by < timezone.localdate():
            raise ValidationError('Needed-by date cannot be in the past.')
        return needed_by


class AcceptIncomingForm(forms.Form):
    location = forms.ChoiceField(choices=Item.LOCATION_CHOICES)
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))

    def clean_date(self):
        from django.utils import timezone
        meetup_date = self.cleaned_data['date']
        if meetup_date < timezone.localdate():
            raise ValidationError('Meetup date cannot be in the past.')
        return meetup_date


class BorrowForm(forms.Form):
    prefix = 'borrow'

    borrow_from = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        error_messages={'required': 'Please select a start date.'}
    )
    return_by = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        error_messages={'required': 'Please select a return date.'}
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 200, 'placeholder': 'Add an optional note to the item owner...'})
    )
    open_request = forms.IntegerField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, item=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.item = item

    def clean_borrow_from(self):
        borrow_from = self.cleaned_data.get('borrow_from')
        if borrow_from and borrow_from < timezone.localdate():
            raise ValidationError('Borrow start date cannot be in the past.')
        return borrow_from

    def clean(self):
        cleaned_data = super().clean()
        borrow_from = cleaned_data.get('borrow_from')
        return_by = cleaned_data.get('return_by')

        if borrow_from and return_by:
            if return_by <= borrow_from:
                self.add_error('return_by', 'Return date must be after the borrow start date.')
            elif self.item and self.item.lend_limit:
                days = (return_by - borrow_from).days
                if days > self.item.lend_limit:
                    limit_label = self.item.get_lend_limit_display().lower()
                    self.add_error('return_by', f'Exceeds lending limit of {limit_label} ({self.item.lend_limit} days).')
        return cleaned_data

class ProfileForm(forms.ModelForm):
    MAX_AVATAR_BYTES = 2 * 1024 * 1024
    school = forms.ChoiceField(choices=[('Mapúa MCM', 'Mapúa MCM')])

    class Meta:
        model = UserProfile
        fields = ('avatar', 'full_name', 'display_name', 'school', 'program', 'year_level', 'bio', 'pickup_spot')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['display_name'].required = True
        self.fields['pickup_spot'].choices = [('', 'No preference')] + LOCATION_CHOICES

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'content_type'):  # only check newly uploaded files
            if avatar.content_type not in ('image/jpeg', 'image/png'):
                raise ValidationError("Upload a JPG or PNG image.")
            if avatar.size > self.MAX_AVATAR_BYTES:
                raise ValidationError("Image must be 2MB or smaller.")
        return avatar


class ShelfPasswordChangeForm(PasswordChangeForm):
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        errors = password_rule_errors(password)
        if password and self.user.check_password(password):
            errors.append("Choose a password different from your current one.")
        if errors:
            raise ValidationError(errors)
        return password