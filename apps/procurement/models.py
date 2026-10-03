"""Procurement module: vendors, requests, quotations, purchase orders."""
from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import OwnedModel, WorkflowMixin
from apps.core.validators import FileSizeValidator, FileTypeValidator


class Vendor(models.Model):
    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField("TIN", max_length=40, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account = models.CharField(max_length=40, blank=True)
    category = models.CharField(max_length=120, blank=True, help_text="e.g. Stationery, Vehicles, IT")
    rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1-5 performance rating")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def get_absolute_url(self):
        return reverse("procurement:vendor_detail", args=[self.pk])

    def __str__(self):
        return self.name


class ProcurementStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    PROCUREMENT = "procurement", "Procurement"
    PURCHASED = "purchased", "Purchased"
    COMPLETED = "completed", "Completed"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class ProcurementRequest(WorkflowMixin, OwnedModel):
    """Procurement request with approval workflow and quotation comparison."""

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="procurement_requests")
    project = models.ForeignKey("programs.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="procurement_requests")
    quantity = models.PositiveIntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    needed_by = models.DateField(null=True, blank=True)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.MEDIUM)
    selected_vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.SET_NULL, related_name="won_requests")

    class Meta:
        ordering = ("-created_at",)
        permissions = [("approve_request", "Can approve procurement requests")]

    def get_absolute_url(self):
        return reverse("procurement:request_detail", args=[self.pk])

    def __str__(self):
        return self.title


class Quotation(models.Model):
    request = models.ForeignKey(ProcurementRequest, on_delete=models.CASCADE, related_name="quotations")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="quotations")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    document = models.FileField(upload_to="quotations/", blank=True, validators=[FileSizeValidator(), FileTypeValidator()])
    is_selected = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("amount",)

    def __str__(self):
        return f"{self.vendor.name}: {self.amount}"


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DELIVERED = "delivered", "Delivered"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    po_number = models.CharField(max_length=20, unique=True, editable=False)
    request = models.ForeignKey(ProcurementRequest, on_delete=models.CASCADE, related_name="purchase_orders")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="purchase_orders")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    order_date = models.DateField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-order_date",)

    def save(self, *args, **kwargs):
        if not self.po_number:
            from django.utils import timezone

            prefix = f"PO-{timezone.localdate():%Y}-"
            count = PurchaseOrder.objects.filter(po_number__startswith=prefix).count() + 1
            self.po_number = f"{prefix}{count:04d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("procurement:po_detail", args=[self.pk])

    def __str__(self):
        return self.po_number
