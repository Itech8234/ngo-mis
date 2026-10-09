"""Forms for authentication and user administration."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Role, User


class GHDIAuthForm(AuthenticationForm):
    """Email-based login form with GHDI styling hooks."""

    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True, "class": "input"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "class": "input"}),
    )

    error_messages = {
        "invalid_login": "Please enter a correct email and password.",
        "inactive": "This account has been deactivated. Contact your administrator.",
    }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "photo", "job_title"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name": forms.TextInput(attrs={"class": "input"}),
            "phone": forms.TextInput(attrs={"class": "input"}),
            "job_title": forms.TextInput(attrs={"class": "input"}),
        }


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username", "role", "job_title", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "username": forms.TextInput(attrs={"class": "input"}),
            "role": forms.Select(attrs={"class": "input"}),
            "job_title": forms.TextInput(attrs={"class": "input"}),
        }


class UserCreateForm(forms.ModelForm):
    """Create an account without collecting or storing a temporary password."""

    department = forms.ModelChoiceField(
        queryset=None, required=False, empty_label="Select department",
        widget=forms.Select(attrs={"class": "input"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.hr.models import Department

        self.fields["department"].queryset = Department.objects.filter(is_active=True).order_by("name")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username", "role", "job_title"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "username": forms.TextInput(attrs={"class": "input"}),
            "role": forms.Select(attrs={"class": "input"}),
            "job_title": forms.TextInput(attrs={"class": "input"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
        return user
