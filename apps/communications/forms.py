"""Communications forms."""
from django import forms

from .models import Announcement, InternalMessage


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "body", "audience", "status", "is_pinned", "publish_at", "expires_at"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 5}),
            "publish_at": forms.DateInput(attrs={"type": "date"}),
            "expires_at": forms.DateInput(attrs={"type": "date"}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = InternalMessage
        fields = ["recipient", "subject", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}
