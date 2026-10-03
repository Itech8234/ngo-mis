"""Website forms: public contact form (CMS ContactMessage) and donation pledges."""
from django import forms

from apps.cms.models import ContactMessage, DonationIntent


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "body"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Your full name", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.org", "autocomplete": "email"}),
            "subject": forms.TextInput(attrs={"class": "form-input", "placeholder": "How can we help?"}),
            "body": forms.Textarea(attrs={"class": "form-textarea", "rows": 5, "placeholder": "Write your message..."}),
        }


class DonationForm(forms.ModelForm):
    class Meta:
        model = DonationIntent
        fields = ["name", "email", "phone", "kind", "amount", "currency", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Your full name", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.org", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+234 … (optional)", "autocomplete": "tel"}),
            "kind": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-input", "placeholder": "Amount (optional)", "min": "0", "step": "0.01"}),
            "currency": forms.Select(attrs={"class": "form-select"}, choices=[("NGN", "NGN ₦"), ("USD", "USD $"), ("EUR", "EUR €"), ("GBP", "GBP £")]),
            "message": forms.Textarea(attrs={"class": "form-textarea", "rows": 4, "placeholder": "Anything we should know? (optional)"}),
        }
