"""Donor, grant and partner views."""
from django.db.models import Sum
from django.shortcuts import redirect

from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView

from .forms import DonorForm, GrantForm, PartnerForm
from .models import Donor, Grant, Partner


class DonorListView(GHDIListView):
    model = Donor
    permission_required = "partners.view_donor"
    search_fields = ("name", "contact_name")
    title = "Donors"


class DonorDetailView(GHDidDetailView):
    model = Donor
    permission_required = "partners.view_donor"
    template_name = "partners/donor_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["grants"] = self.object.grants.all()
        context["projects"] = self.object.projects.select_related("program", "manager")
        context["funds_received"] = self.object.funds_received
        context["funds_spent"] = self.object.funds_spent
        return context


class DonorCreateView(GHDICreateView):
    model = Donor
    form_class = DonorForm
    permission_required = "partners.add_donor"
    template_name = "partners/donor_form.html"
    title = "New Donor"


class DonorUpdateView(GHDIUpdateView):
    model = Donor
    form_class = DonorForm
    permission_required = "partners.change_donor"
    template_name = "partners/donor_form.html"
    title = "Edit Donor"


class GrantListView(GHDIListView):
    model = Grant
    permission_required = "partners.view_grant"
    search_fields = ("name", "code")
    title = "Grants"


class GrantDetailView(GHDidDetailView):
    model = Grant
    permission_required = "partners.view_grant"
    template_name = "partners/grant_detail.html"


class GrantCreateView(GHDICreateView):
    model = Grant
    form_class = GrantForm
    permission_required = "partners.add_grant"
    template_name = "partners/grant_form.html"
    title = "New Grant"


class GrantUpdateView(GHDIUpdateView):
    model = Grant
    form_class = GrantForm
    permission_required = "partners.change_grant"
    template_name = "partners/grant_form.html"
    title = "Edit Grant"


class PartnerListView(GHDIListView):
    model = Partner
    permission_required = "partners.view_partner"
    search_fields = ("name", "contact_person")
    title = "Partners"

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("programs", "projects")
        ptype = self.request.GET.get("type")
        if ptype:
            qs = qs.filter(partner_type=ptype)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["types"] = Partner.PartnerType.choices
        return context


class PartnerDetailView(GHDidDetailView):
    model = Partner
    permission_required = "partners.view_partner"
    template_name = "partners/partner_detail.html"


class PartnerCreateView(GHDICreateView):
    model = Partner
    form_class = PartnerForm
    permission_required = "partners.add_partner"
    template_name = "partners/partner_form.html"
    title = "New Partner"


class PartnerUpdateView(GHDIUpdateView):
    model = Partner
    form_class = PartnerForm
    permission_required = "partners.change_partner"
    template_name = "partners/partner_form.html"
    title = "Edit Partner"
