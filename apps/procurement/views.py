"""Procurement views: requests (workflow), vendors, quotations, POs."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView
from apps.core.services import WorkflowService, notify

from .forms import ProcurementRequestForm, PurchaseOrderForm, QuotationForm, VendorForm
from .models import ProcurementRequest, ProcurementStatus, PurchaseOrder, Quotation, Vendor

User = get_user_model()


class RequestListView(GHDIListView):
    model = ProcurementRequest
    permission_required = "procurement.view_procurementrequest"
    search_fields = ("title", "description")
    title = "Procurement Requests"
    template_name = "procurement/request_list.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("requested_by", "project", "selected_vendor")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = ProcurementStatus.choices
        return context


class RequestDetailView(GHDidDetailView):
    model = ProcurementRequest
    permission_required = "procurement.view_procurementrequest"
    template_name = "procurement/request_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["quotations"] = self.object.quotations.select_related("vendor")
        context["quotation_form"] = QuotationForm()
        context["po_form"] = PurchaseOrderForm()
        context["selected_quotation"] = self.object.quotations.filter(is_selected=True).select_related("vendor").first()
        context["history"] = WorkflowService(self.object, self.request.user).history()
        return context


class RequestCreateView(GHDICreateView):
    model = ProcurementRequest
    form_class = ProcurementRequestForm
    permission_required = "procurement.add_procurementrequest"
    template_name = "procurement/request_form.html"
    title = "New Procurement Request"

    def form_valid(self, form):
        form.instance.requested_by = self.request.user
        response = super().form_valid(form)
        WorkflowService(self.object, self.request.user).submit(
            notify_users=User.objects.filter(role__in=["proc", "exec"], is_active=True),
            step="supervisor",
        )
        messages.success(self.request, "Procurement request submitted for approval.")
        return response


class RequestUpdateView(GHDIUpdateView):
    model = ProcurementRequest
    form_class = ProcurementRequestForm
    permission_required = "procurement.change_procurementrequest"
    template_name = "procurement/request_form.html"
    title = "Edit Request"


@login_required
@permission_required("procurement.approve_request", raise_exception=True)
@require_POST
def request_review(request, pk):
    """Workflow actions on a procurement request."""
    request_obj = get_object_or_404(ProcurementRequest, pk=pk)
    action = request.POST.get("action", "")
    note = request.POST.get("note", "")
    service = WorkflowService(request_obj, request.user)
    allowed_statuses = {
        "review": {ProcurementStatus.SUBMITTED},
        "approve": {ProcurementStatus.SUBMITTED, ProcurementStatus.UNDER_REVIEW},
        "reject": {ProcurementStatus.SUBMITTED, ProcurementStatus.UNDER_REVIEW},
        "procurement": {ProcurementStatus.APPROVED},
        "purchase": {ProcurementStatus.PROCUREMENT},
        "complete": {ProcurementStatus.PURCHASED},
        "cancel": {ProcurementStatus.DRAFT, ProcurementStatus.SUBMITTED, ProcurementStatus.UNDER_REVIEW,
                   ProcurementStatus.APPROVED, ProcurementStatus.PROCUREMENT, ProcurementStatus.PURCHASED},
    }
    if action not in allowed_statuses or request_obj.status not in allowed_statuses[action]:
        messages.error(request, "That action is not available for the current request status.")
        return redirect("procurement:request_detail", pk)
    if action == "review":
        service.review(step="supervisor", note=note)
        messages.success(request, "Request moved to review.")
    elif action == "approve":
        service.approve(step="executive", note=note)
        request_obj.status = ProcurementStatus.APPROVED
        request_obj.save(update_fields=["status", "updated_at"])
        messages.success(request, "Procurement request approved.")
    elif action == "reject":
        service.reject(note=note)
        messages.warning(request, "Procurement request rejected.")
    elif action == "procurement":
        request_obj.status = ProcurementStatus.PROCUREMENT
        request_obj.save(update_fields=["status", "updated_at"])
        service._record("procurement", "update", note)
        messages.success(request, "Request moved to the procurement phase.")
    elif action == "purchase":
        request_obj.status = ProcurementStatus.PURCHASED
        request_obj.save(update_fields=["status", "updated_at"])
        service._record("procurement", "purchase", note)
        messages.success(request, "Items purchased.")
    elif action == "complete":
        service.complete(note=note)
        messages.success(request, "Procurement request completed.")
    elif action == "cancel":
        service.cancel(note=note)
        messages.info(request, "Procurement request cancelled.")
    return redirect("procurement:request_detail", pk)


@login_required
@permission_required("procurement.add_quotation", raise_exception=True)
@db_transaction.atomic
@require_POST
def quotation_add(request, pk):
    request_obj = get_object_or_404(ProcurementRequest, pk=pk)
    if request_obj.status != ProcurementStatus.PROCUREMENT:
        messages.error(request, "Quotations can only be added during the procurement stage.")
        return redirect("procurement:request_detail", pk)
    form = QuotationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        quotation = form.save(commit=False)
        quotation.request = request_obj
        quotation.save()
        messages.success(request, "Quotation added.")
    return redirect("procurement:request_detail", pk)


@login_required
@permission_required("procurement.add_quotation", raise_exception=True)
@db_transaction.atomic
@require_POST
def quotation_select(request, pk, quotation_id):
    request_obj = get_object_or_404(ProcurementRequest, pk=pk)
    if request_obj.status != ProcurementStatus.PROCUREMENT:
        messages.error(request, "A quotation can only be selected during the procurement stage.")
        return redirect("procurement:request_detail", pk)
    quotation = get_object_or_404(Quotation, pk=quotation_id, request=request_obj)
    request_obj.quotations.update(is_selected=False)
    quotation.is_selected = True
    quotation.save()
    request_obj.selected_vendor = quotation.vendor
    request_obj.save(update_fields=["selected_vendor", "updated_at"])
    messages.success(request, f"{quotation.vendor.name} selected as the winning vendor.")
    return redirect("procurement:request_detail", pk)


@login_required
@permission_required("procurement.add_purchaseorder", raise_exception=True)
@db_transaction.atomic
@require_POST
def po_create(request, pk):
    request_obj = get_object_or_404(ProcurementRequest, pk=pk)
    selected_quote = request_obj.quotations.filter(is_selected=True, vendor=request_obj.selected_vendor).first()
    if request_obj.status != ProcurementStatus.PROCUREMENT or selected_quote is None:
        messages.error(request, "Select a quotation during the procurement stage before creating a purchase order.")
        return redirect("procurement:request_detail", pk)
    form = PurchaseOrderForm(request.POST or None)
    form.fields["vendor"].queryset = Vendor.objects.filter(pk=request_obj.selected_vendor_id)
    if request.method == "POST" and form.is_valid():
        if form.cleaned_data["vendor"].pk != selected_quote.vendor_id or form.cleaned_data["amount"] != selected_quote.amount:
            messages.error(request, "The purchase order vendor and amount must match the selected quotation.")
            return redirect("procurement:request_detail", pk)
        po = form.save(commit=False)
        po.request = request_obj
        po.save()
        messages.success(request, f"Purchase order {po.po_number} created.")
    return redirect("procurement:request_detail", pk)


class VendorListView(GHDIListView):
    model = Vendor
    permission_required = "procurement.view_vendor"
    search_fields = ("name", "category", "contact_person")
    title = "Vendors"


class VendorDetailView(GHDidDetailView):
    model = Vendor
    permission_required = "procurement.view_vendor"
    template_name = "procurement/vendor_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["quotations"] = self.object.quotations.select_related("request")[:20]
        context["purchase_orders"] = self.object.purchase_orders.select_related("request")[:20]
        return context


class VendorCreateView(GHDICreateView):
    model = Vendor
    form_class = VendorForm
    permission_required = "procurement.add_vendor"
    template_name = "procurement/vendor_form.html"
    title = "Register Vendor"


class VendorUpdateView(GHDIUpdateView):
    model = Vendor
    form_class = VendorForm
    permission_required = "procurement.change_vendor"
    template_name = "procurement/vendor_form.html"
    title = "Edit Vendor"


class PurchaseOrderListView(GHDIListView):
    model = PurchaseOrder
    permission_required = "procurement.view_purchaseorder"
    search_fields = ("po_number",)
    title = "Purchase Orders"


class PurchaseOrderDetailView(GHDidDetailView):
    model = PurchaseOrder
    permission_required = "procurement.view_purchaseorder"
    template_name = "procurement/po_detail.html"


@login_required
@permission_required("procurement.change_purchaseorder", raise_exception=True)
@require_POST
def po_update_status(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    status = request.POST.get("status")
    if status in PurchaseOrder.Status.values and not (
        status == PurchaseOrder.Status.CLOSED and po.status != PurchaseOrder.Status.DELIVERED
    ):
        po.status = status
        po.save(update_fields=["status"])
        messages.success(request, "Purchase order updated.")
    return redirect("procurement:po_detail", pk)

