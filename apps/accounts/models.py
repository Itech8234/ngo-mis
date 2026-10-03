"""GHDI custom user model with role-based access control."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class Role(models.TextChoices):
    """Primary GHDI roles. Permissions per role live in accounts.permissions."""

    ADMIN = "admin", "Super Administrator"
    EXEC = "exec", "Executive Director"
    HR = "hr", "Human Resource Officer"
    PM = "pm", "Program Manager"
    FIN = "fin", "Finance Officer"
    MEAL = "meal", "MEAL Officer"
    PROC = "proc", "Procurement Officer"
    STAFF = "staff", "Staff"
    VIEWER = "viewer", "Viewer"
    CONTENT = "content", "Content Manager"


class User(AbstractUser):
    """Custom user: email login, role, profile photo, 2FA placeholder."""

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF, db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to="avatars/", blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    two_factor_enabled = models.BooleanField(default=False, help_text="Architecture placeholder for TOTP two-factor authentication.")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        ordering = ("first_name", "last_name")
        permissions = [
            ("view_executive_dashboard", "Can view the Executive Director dashboard"),
            ("export_report", "Can export reports"),
        ]

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def get_initials(self):
        parts = [p for p in (self.first_name, self.last_name) if p]
        if parts:
            return "".join(p[0] for p in parts).upper()[:2]
        name = self.username or "G"
        return name[:2].upper()

    def get_dashboard_url(self):
        from .permissions import DASHBOARD_BY_ROLE

        return reverse(DASHBOARD_BY_ROLE.get(self.role, "dashboard:staff"))

    def __str__(self):
        return self.full_name
