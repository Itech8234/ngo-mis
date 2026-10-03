"""Asset register views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView

from .forms import AssetAssignmentForm, AssetForm
from .models import Asset, AssetAssignment


class AssetListView(GHDIListView):
    model = Asset
    permission_required = "assets.view_asset"
    search_fields = ("name", "asset_tag", "serial_number")
    title = "Asset Register"

    def get_queryset(self):
        qs = super().get_queryset().select_related("location", "assigned_to")
        status = self.request.GET.get("status")
        category = self.request.GET.get("category")
        if status:
            qs = qs.filter(status=status)
        if category:
            qs = qs.filter(category=category)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Asset.Status.choices
        context["categories"] = Asset.Category.choices
        return context


class AssetDetailView(GHDidDetailView):
    model = Asset
    permission_required = "assets.view_asset"
    template_name = "assets/asset_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["assignments"] = self.object.assignments.select_related("employee", "recorded_by")
        context["assign_form"] = AssetAssignmentForm()
        return context


class AssetCreateView(GHDICreateView):
    model = Asset
    form_class = AssetForm
    permission_required = "assets.add_asset"
    template_name = "assets/asset_form.html"
    title = "Register Asset"


class AssetUpdateView(GHDIUpdateView):
    model = Asset
    form_class = AssetForm
    permission_required = "assets.change_asset"
    template_name = "assets/asset_form.html"
    title = "Edit Asset"


@login_required
@permission_required("assets.change_asset", raise_exception=True)
def asset_assign(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    form = AssetAssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        assignment = form.save(commit=False)
        assignment.asset = asset
        assignment.recorded_by = request.user
        assignment.save()
        asset.assigned_to = assignment.employee
        asset.status = Asset.Status.IN_USE
        asset.save(update_fields=["assigned_to", "status", "updated_at"])
        messages.success(request, f"Asset assigned to {assignment.employee.full_name}.")
    return redirect("assets:asset_detail", pk)


@login_required
@permission_required("assets.change_asset", raise_exception=True)
@require_POST
def asset_return(request, pk, assignment_id):
    asset = get_object_or_404(Asset, pk=pk)
    assignment = get_object_or_404(AssetAssignment, pk=assignment_id, asset=asset)
    from django.utils import timezone

    assignment.return_date = timezone.localdate()
    assignment.condition_in = request.POST.get("condition_in", Asset.Condition.GOOD)
    assignment.save(update_fields=["return_date", "condition_in"])
    asset.assigned_to = None
    asset.status = Asset.Status.IN_STORE
    asset.save(update_fields=["assigned_to", "status", "updated_at"])
    messages.success(request, "Asset returned to store.")
    return redirect("assets:asset_detail", pk)
