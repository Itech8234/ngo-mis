"""Procurement forms."""
from django import forms

from .models import ProcurementRequest, PurchaseOrder, Quotation, Vendor


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "contact_person", "phone", "email", "address", "tax_id", "bank_name", "bank_account", "category", "rating", "is_active"]


class ProcurementRequestForm(forms.ModelForm):
    class Meta:
        model = ProcurementRequest
        fields = ["title", "description", "project", "quantity", "estimated_cost", "needed_by", "priority"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "needed_by": forms.DateInput(attrs={"type": "date"}),
        }


class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ["vendor", "amount", "document", "notes"]


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["vendor", "amount", "expected_delivery", "notes"]
        widgets = {"expected_delivery": forms.DateInput(attrs={"type": "date"})}
