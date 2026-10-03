"""Internal communications: announcements and messages."""
from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import OwnedModel


class Announcement(OwnedModel):
    """Organisational announcement published (by ED/HR/Admin) on dashboards."""

    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        PROGRAMS = "programs", "Programs"
        FINANCE = "finance", "Finance"
        HR = "hr", "HR"
        ADMIN = "admin", "Administration"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.ALL)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    is_pinned = models.BooleanField(default=False)
    publish_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ("-is_pinned", "-created_at")
        permissions = [("publish_announcement", "Can publish announcements")]

    def get_absolute_url(self):
        return reverse("communications:announcement_detail", args=[self.pk])

    def __str__(self):
        return self.title


class InternalMessage(models.Model):
    """Simple internal message (threaded via parent)."""

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    subject = models.CharField(max_length=200)
    body = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies")
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def get_absolute_url(self):
        return reverse("communications:inbox")

    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.subject}"
