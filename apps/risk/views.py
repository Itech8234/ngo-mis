"""Risk register and incident views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect

from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView

from .forms import IncidentForm, RiskForm
from .models import Incident, Risk


class RiskListView(GHDIListView):
    model = Risk
    permission_required = "risk.view_risk"
    search_fields = ("title", "description")
    title = "Risk Register"

    def get_queryset(self):
        qs = super().get_queryset().select_related("responsible")
        category = self.request.GET.get("category")
        level = self.request.GET.get("level")
        if category:
            qs = qs.filter(category=category)
        if level == "high":
            qs = [r for r in qs if r.level == "high"]
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Risk.Category.choices
        return context


class RiskDetailView(GHDidDetailView):
    model = Risk
    permission_required = "risk.view_risk"
    template_name = "risk/risk_detail.html"


class RiskCreateView(GHDICreateView):
    model = Risk
    form_class = RiskForm
    permission_required = "risk.add_risk"
    template_name = "risk/risk_form.html"
    title = "Register Risk"


class RiskUpdateView(GHDIUpdateView):
    model = Risk
    form_class = RiskForm
    permission_required = "risk.change_risk"
    template_name = "risk/risk_form.html"
    title = "Edit Risk"


class IncidentListView(GHDIListView):
    model = Incident
    permission_required = "risk.view_incident"
    search_fields = ("title", "description", "location")
    title = "Incidents"

    def get_queryset(self):
        qs = super().get_queryset().select_related("reported_by", "assigned_to")
        severity = self.request.GET.get("severity")
        status = self.request.GET.get("status")
        if severity:
            qs = qs.filter(severity=severity)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["severities"] = Incident.Severity.choices
        context["statuses"] = Incident.Status.choices
        return context


class IncidentDetailView(GHDidDetailView):
    model = Incident
    permission_required = "risk.view_incident"
    template_name = "risk/incident_detail.html"


class IncidentCreateView(GHDICreateView):
    model = Incident
    form_class = IncidentForm
    permission_required = "risk.add_incident"
    template_name = "risk/incident_form.html"
    title = "Report Incident"

    def form_valid(self, form):
        form.instance.reported_by = self.request.user
        return super().form_valid(form)


class IncidentUpdateView(GHDIUpdateView):
    model = Incident
    form_class = IncidentForm
    permission_required = "risk.change_incident"
    template_name = "risk/incident_form.html"
    title = "Update Incident"
