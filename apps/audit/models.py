"""Immutable audit trail for GHDI. Audit rows are append-only for normal users."""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Records security- and business-relevant events. Never user-editable."""

    class Action(models.TextChoices):
        LOGIN = "login", "Login"
        LOGIN_FAILED = "login_failed", "Failed Login"
        LOGOUT = "logout", "Logout"
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        SUBMIT = "submit", "Submit"
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        EXPORT = "export", "Export"
        DOWNLOAD = "download", "Download"
        PASSWORD_CHANGE = "password_change", "Password Change"
        PERMISSION_CHANGE = "permission_change", "Permission Change"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=30, choices=Action.choices, db_index=True)
    module = models.CharField(max_length=50, blank=True, db_index=True)
    model = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "audit log entry"
        verbose_name_plural = "audit log entries"

    def __str__(self):
        who = self.username or "anonymous"
        return f"{who} {self.action} {self.model} {self.object_repr}".strip()

    @property
    def action_badge(self):
        return {
            "login": "badge-blue", "logout": "badge-gray", "create": "badge-green",
            "update": "badge-amber", "delete": "badge-red", "approve": "badge-green",
            "reject": "badge-red", "submit": "badge-blue", "export": "badge-gray",
            "download": "badge-gray", "password_change": "badge-amber",
            "permission_change": "badge-red", "login_failed": "badge-red",
        }.get(self.action, "badge-gray")
