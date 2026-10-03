"""Beneficiary management. PII access is permission-gated (view_pii)."""
from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import Location, OwnedModel
from apps.core.validators import FileSizeValidator, FileTypeValidator


class Beneficiary(OwnedModel):
    """Beneficiary record. Personal identifiers are hidden without view_pii."""

    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    class AgeGroup(models.TextChoices):
        CHILD = "child", "Child (0-17)"
        YOUTH = "youth", "Youth (18-35)"
        ADULT = "adult", "Adult (36-59)"
        OLDER = "older", "Older Person (60+)"

    class VulnerabilityCategory(models.TextChoices):
        IDP = "idp", "Internally Displaced Person"
        RETURNEE = "returnee", "Returnee"
        HOST = "host", "Host Community"
        PWD = "pwd", "Person with Disability"
        FHH = "fhh", "Female-Headed Household"
        ORPHAN = "orphan", "Orphan / Vulnerable Child"
        ELDERLY = "elderly", "Older Person at Risk"
        OTHER = "other", "Other Vulnerability"

    code = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    date_of_birth = models.DateField(null=True, blank=True)
    age_group = models.CharField(max_length=10, choices=AgeGroup.choices, db_index=True)
    phone = models.CharField(max_length=50, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="beneficiaries")
    community = models.CharField(max_length=120, blank=True)
    vulnerability_category = models.CharField(max_length=12, choices=VulnerabilityCategory.choices, db_index=True)
    has_disability = models.BooleanField(default=False)
    household_size = models.PositiveSmallIntegerField(default=1)
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="beneficiaries")
    program = models.ForeignKey("programs.Program", null=True, blank=True, on_delete=models.SET_NULL, related_name="beneficiaries")
    registration_date = models.DateField(auto_now_add=True)
    photo = models.ImageField(upload_to="beneficiaries/", blank=True, validators=[FileSizeValidator(), FileTypeValidator({"jpg", "jpeg", "png"})])
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("code",)
        permissions = [("view_pii", "Can view beneficiary personally identifiable information")]
        indexes = [models.Index(fields=("gender", "age_group"))]

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = "BEN-"
            last = Beneficiary.objects.order_by("-pk").first()
            next_num = (int(last.code.split("-")[-1]) + 1) if last and last.code.startswith(prefix) else 1
            self.code = f"{prefix}{next_num:05d}"
        super().save(*args, **kwargs)

    @property
    def masked_name(self):
        """Privacy-aware display for users without PII permission."""
        parts = self.full_name.split()
        if len(parts) == 1:
            return f"{parts[0][0]}***"
        return f"{parts[0][0]}*** {parts[-1][0]}***"

    def get_absolute_url(self):
        return reverse("beneficiaries:beneficiary_detail", args=[self.pk])

    def __str__(self):
        return f"{self.code}"


class AssistanceRecord(models.Model):
    """One assistance/entitlement delivered to a beneficiary."""

    class AssistanceType(models.TextChoices):
        CASH = "cash", "Cash Transfer"
        FOOD = "food", "Food Assistance"
        NFI = "nfi", "Non-Food Items"
        SHELTER = "shelter", "Shelter"
        EDUCATION = "education", "Education Support"
        PROTECTION = "protection", "Protection Service"
        TRAINING = "training", "Training / Capacity Building"
        HEALTH = "health", "Health"
        WASH = "wash", "WASH"
        OTHER = "other", "Other"

    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name="assistance_records")
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="assistance_records")
    assistance_type = models.CharField(max_length=12, choices=AssistanceType.choices, db_index=True)
    date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ("-date",)

    def __str__(self):
        return f"{self.beneficiary.code} - {self.assistance_type}"
