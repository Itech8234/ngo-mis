"""Forms for core organisation and system settings."""
from django import forms

from .models import OrganizationSetting, SystemSetting
from .validators import FileSizeValidator, FileTypeValidator


class OrganizationSettingForm(forms.ModelForm):
    class Meta:
        model = OrganizationSetting
        fields = [
            "name", "acronym", "tagline", "logo", "address", "email", "phone",
            "website", "registration_number", "mission", "vision", "currency",
            "fiscal_year_start",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "acronym": forms.TextInput(attrs={"class": "input"}),
            "tagline": forms.TextInput(attrs={"class": "input"}),
            "address": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "phone": forms.TextInput(attrs={"class": "input"}),
            "website": forms.URLInput(attrs={"class": "input"}),
            "registration_number": forms.TextInput(attrs={"class": "input"}),
            "mission": forms.Textarea(attrs={"class": "input", "rows": 3}),
            "vision": forms.Textarea(attrs={"class": "input", "rows": 3}),
            "currency": forms.TextInput(attrs={"class": "input"}),
            "fiscal_year_start": forms.NumberInput(attrs={"class": "input", "min": 1, "max": 12}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].validators = [FileSizeValidator(), FileTypeValidator({"jpg", "jpeg", "png", "webp", "svg"})]


class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = ["key", "value", "description"]
        widgets = {
            "key": forms.TextInput(attrs={"class": "input"}),
            "value": forms.TextInput(attrs={"class": "input"}),
            "description": forms.TextInput(attrs={"class": "input"}),
        }
