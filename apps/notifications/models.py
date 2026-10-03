"""Notification model and services for GHDI."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """In-app notification shown in the topbar and notifications page."""

    class Type(models.TextChoices):
        APPROVAL = "approval", "Approval"
        REMINDER = "reminder", "Reminder"
        DEADLINE = "deadline", "Deadline"
        MESSAGE = "message", "Message"
        PROGRAM = "program", "Program"
        FINANCE = "finance", "Finance"
        HR = "hr", "HR"
        SYSTEM = "system", "System"
        SECURITY = "security", "Security"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM, db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("recipient", "is_read"))]

    def __str__(self):
        return self.title

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    @property
    def type_badge(self):
        return {
            "approval": "badge-green", "reminder": "badge-amber", "deadline": "badge-red",
            "message": "badge-blue", "program": "badge-blue", "finance": "badge-amber",
            "hr": "badge-gray", "system": "badge-gray", "security": "badge-red",
        }.get(self.type, "badge-gray")
