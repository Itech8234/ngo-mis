"""Beneficiaries views with privacy-aware PII gating."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView

from .forms import AssistanceRecordForm, BeneficiaryForm
from .models import AssistanceRecord, Beneficiary

User = get_user_model()


class BeneficiaryListView(GHDIListView):
    model = Beneficiary
    permission_required = "beneficiaries.view_beneficiary"
    search_fields = ("code", "full_name", "community")
    title = "Beneficiaries"

    def get_queryset(self):
        qs = super().get_queryset().select_related("location", "project", "program")
        gender = self.request.GET.get("gender")
        category = self.request.GET.get("category")
        age_group = self.request.GET.get("age_group")
        if gender:
            qs = qs.filter(gender=gender)
        if category:
            qs = qs.filter(vulnerability_category=category)
        if age_group:
            qs = qs.filter(age_group=age_group)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "total": Beneficiary.objects.filter(is_active=True).count(),
                "by_gender": list(Beneficiary.objects.values("gender").annotate(total=Count("id")).order_by("gender")),
                "by_age": list(Beneficiary.objects.values("age_group").annotate(total=Count("id")).order_by("age_group")),
                "by_category": list(Beneficiary.objects.values("vulnerability_category").annotate(total=Count("id")).order_by("vulnerability_category")),
                "by_lga": list(
                    Beneficiary.objects.values("location__lga").annotate(total=Count("id")).order_by("-total")[:12]
                ),
                "show_pii": self.request.user.has_perm("beneficiaries.view_pii"),
                "genders": Beneficiary.Gender.choices,
                "categories": Beneficiary.VulnerabilityCategory.choices,
                "age_groups": Beneficiary.AgeGroup.choices,
            }
        )
        return context


class BeneficiaryDetailView(GHDidDetailView):
    model = Beneficiary
    permission_required = "beneficiaries.view_beneficiary"
    template_name = "beneficiaries/beneficiary_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_pii"] = self.request.user.has_perm("beneficiaries.view_pii")
        context["assistance"] = self.object.assistance_records.select_related("project")[:20]
        context["assistance_form"] = AssistanceRecordForm()
        context["assistance_total"] = self.object.assistance_records.aggregate(t=Sum("value"))["t"] or 0
        return context


class BeneficiaryCreateView(GHDICreateView):
    model = Beneficiary
    form_class = BeneficiaryForm
    permission_required = "beneficiaries.add_beneficiary"
    template_name = "beneficiaries/beneficiary_form.html"
    title = "Register Beneficiary"


class BeneficiaryUpdateView(GHDIUpdateView):
    model = Beneficiary
    form_class = BeneficiaryForm
    permission_required = "beneficiaries.change_beneficiary"
    template_name = "beneficiaries/beneficiary_form.html"
    title = "Edit Beneficiary"


@login_required
@permission_required("beneficiaries.add_beneficiary", raise_exception=True)
def assistance_create(request, pk):
    beneficiary = get_object_or_404(Beneficiary, pk=pk)
    form = AssistanceRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.beneficiary = beneficiary
        record.save()
        messages.success(request, "Assistance recorded.")
    return redirect("beneficiaries:beneficiary_detail", pk)
