"""Asset register with assignment history."""
from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import OwnedModel
from apps.core.validators import FileSizeValidator, FileTypeValidator


class Asset(OwnedModel):
    class Category(models.TextChoices):
        VEHICLE = "vehicle", "Vehicle"
        IT = "it", "IT Equipment"
        FURNITURE = "furniture", "Furniture"
        OFFICE = "office", "Office Equipment"
        FIELD = "field", "Field Equipment"
        COMMUNICATION = "communication", "Communication"
        OTHER = "other", "Other"

    class Condition(models.TextChoices):
        NEW = "new", "New"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"
        DAMAGED = "damaged", "Damaged"

    class Status(models.TextChoices):
        IN_USE = "in_use", "In Use"
        IN_STORE = "in_store", "In Store"
        MAINTENANCE = "under_maintenance", "Under Maintenance"
        DISPOSED = "disposed", "Disposed"
        LOST = "lost", "Lost"

    asset_tag = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=15, choices=Category.choices, db_index=True)
    description = models.TextField(blank=True)
    serial_number = models.CharField(max_length=80, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    current_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    location = models.ForeignKey("core.Location", null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    assigned_to = models.ForeignKey("hr.Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    condition = models.CharField(max_length=10, choices=Condition.choices, default=Condition.GOOD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_USE, db_index=True)
    warranty_until = models.DateField(null=True, blank=True)
    document = models.FileField(upload_to="assets/", blank=True, validators=[FileSizeValidator(), FileTypeValidator()])
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("asset_tag",)

    def save(self, *args, **kwargs):
        if not self.asset_tag:
            from django.utils import timezone

            prefix = f"AST-{timezone.localdate():%Y}-"
            count = Asset.objects.filter(asset_tag__startswith=prefix).count() + 1
            self.asset_tag = f"{prefix}{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("assets:asset_detail", args=[self.pk])

    def __str__(self):
        return f"{self.asset_tag} - {self.name}"


class AssetAssignment(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="assignments")
    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="asset_assignments")
    assigned_date = models.DateField(auto_now_add=True)
    return_date = models.DateField(null=True, blank=True)
    condition_out = models.CharField(max_length=10, choices=Asset.Condition.choices, default=Asset.Condition.GOOD)
    condition_in = models.CharField(max_length=10, choices=Asset.Condition.choices, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ("-assigned_date",)

    def __str__(self):
        return f"{self.asset.asset_tag} -> {self.employee.full_name}"
