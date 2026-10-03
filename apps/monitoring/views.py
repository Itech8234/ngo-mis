"""MEAL views: indicators, data updates and reports."""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Avg, Count, F, Q, Sum
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.audit.middleware import log_action
from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView
from apps.core.services import WorkflowService, notify
from apps.programs.models import Program

from .forms import FeedbackCaseForm, FeedbackReviewForm, IndicatorForm, IndicatorUpdateForm, MEALReportForm
from .models import FeedbackCase, Indicator, IndicatorUpdate, MEALReport

User = get_user_model()

FEEDBACK_TRANSITIONS = {
    FeedbackCase.Status.RECEIVED: {FeedbackCase.Status.UNDER_REVIEW, FeedbackCase.Status.REFERRED, FeedbackCase.Status.RESOLVED},
    FeedbackCase.Status.UNDER_REVIEW: {FeedbackCase.Status.REFERRED, FeedbackCase.Status.RESOLVED},
    FeedbackCase.Status.REFERRED: {FeedbackCase.Status.UNDER_REVIEW, FeedbackCase.Status.RESOLVED},
    FeedbackCase.Status.RESOLVED: {FeedbackCase.Status.CLOSED},
}


class IndicatorListView(GHDIListView):
    model = Indicator
    permission_required = "monitoring.view_indicator"
    search_fields = ("name", "code", "definition")
    title = "Indicators"
    template_name = "monitoring/indicator_list.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("program", "project", "responsible")
        status = self.request.GET.get("performance")
        program = self.request.GET.get("program")
        if status == "below":
            qs = qs.filter(Q(target=0) | Q(current__lt=F("target") * Decimal("0.7")))
        elif status == "ontrack":
            qs = qs.filter(target__gt=0, current__gte=F("target") * Decimal("0.7"))
        if program:
            qs = qs.filter(program_id=program)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Indicator.objects.all()
        context.update(
            {
                "total": qs.count(),
                "below_target": qs.filter(Q(target=0) | Q(current__lt=F("target") * Decimal("0.7"))).count(),
                "programs": Program.objects.all(),
                "performance_choices": (("below", "Below target"), ("ontrack", "On track")),
            }
        )
        return context


class IndicatorDetailView(GHDidDetailView):
    model = Indicator
    permission_required = "monitoring.view_indicator"
    template_name = "monitoring/indicator_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["updates"] = self.object.updates.select_related("recorded_by")[:20]
        context["update_form"] = IndicatorUpdateForm()
        return context


class IndicatorCreateView(GHDICreateView):
    model = Indicator
    form_class = IndicatorForm
    permission_required = "monitoring.add_indicator"
    template_name = "monitoring/indicator_form.html"
    title = "New Indicator"


class IndicatorUpdateView(GHDIUpdateView):
    model = Indicator
    form_class = IndicatorForm
    permission_required = "monitoring.change_indicator"
    template_name = "monitoring/indicator_form.html"
    title = "Edit Indicator"


@login_required
@permission_required("monitoring.add_indicatorupdate", raise_exception=True)
def indicator_update_create(request, pk=None):
    """Log an indicator data point; recalculates the indicator's current value.

    Reachable three ways:
    - ``indicators/<pk>/updates/new/``  indicator fixed by the URL
    - ``indicator-updates/new/?indicator=<pk>``  indicator chosen via query string
    - ``indicator-updates/new/``  bare entry point (e.g. the "Log Indicator"
      quick action): the user picks an indicator from a select instead of the
      page 404-ing.
    """
    indicator_id = pk or request.POST.get("indicator") or request.GET.get("indicator")
    indicator = get_object_or_404(Indicator, pk=indicator_id) if indicator_id else None

    form = IndicatorUpdateForm(request.POST or None)
    if request.method == "POST":
        if indicator is None:
            messages.error(request, "Please choose the indicator you are reporting on.")
        elif form.is_valid():
            with transaction.atomic():
                indicator = Indicator.objects.select_for_update().get(pk=indicator.pk)
                update = form.save(commit=False)
                update.indicator = indicator
                update.recorded_by = request.user
                update.save()
                latest = indicator.updates.order_by("-period", "-created_at").first()
                indicator.current = latest.value if latest else indicator.current
                indicator.save(update_fields=["current", "updated_at"])
            messages.success(request, f"Data logged for {indicator.code}.")
            return redirect("monitoring:indicator_detail", indicator.pk)

    indicators = Indicator.objects.select_related("program", "project").order_by("code")
    return render(
        request,
        "monitoring/indicator_update_form.html",
        {
            "form": form,
            "indicators": indicators,
            "indicator": indicator,
            "cancel_url": indicator.get_absolute_url() if indicator else reverse("monitoring:indicator_list"),
            "page_title": "Log Indicator Data" if indicator else "Log Indicator Data",
        },
    )


class ReportListView(GHDIListView):
    model = MEALReport
    permission_required = "monitoring.view_mealreport"
    search_fields = ("title", "summary")
    title = "MEAL Reports"
    template_name = "monitoring/report_list.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("program", "project", "submitted_by")
        status = self.request.GET.get("status")
        report_type = self.request.GET.get("report_type")
        if status:
            qs = qs.filter(status=status)
        if report_type:
            qs = qs.filter(report_type=report_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = MEALReport.Status.choices
        context["report_types"] = MEALReport.ReportType.choices
        return context


class ReportDetailView(GHDidDetailView):
    model = MEALReport
    permission_required = "monitoring.view_mealreport"
    template_name = "monitoring/report_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["history"] = WorkflowService(self.object, self.request.user).history()
        context["report_sections"] = [
            ("Summary", self.object.summary),
            ("Achievements", self.object.achievements),
            ("Challenges", self.object.challenges),
            ("Lessons learned", self.object.lessons),
        ]
        return context


class ReportCreateView(GHDICreateView):
    model = MEALReport
    form_class = MEALReportForm
    permission_required = "monitoring.add_mealreport"
    template_name = "monitoring/report_form.html"
    title = "New MEAL Report"

    def form_valid(self, form):
        response = super().form_valid(form)
        WorkflowService(self.object, self.request.user).submit(
            notify_users=User.objects.filter(role__in=["exec", "pm", "admin"], is_active=True),
            step="supervisor",
        )
        messages.success(self.request, "Report submitted for review.")
        return response


class ReportUpdateView(GHDIUpdateView):
    model = MEALReport
    form_class = MEALReportForm
    permission_required = "monitoring.change_mealreport"
    template_name = "monitoring/report_form.html"
    title = "Edit Report"

    def dispatch(self, request, *args, **kwargs):
        report = self.get_object()
        if not report.is_editable:
            messages.error(request, "Only draft or returned MEAL reports can be edited.")
            return redirect("monitoring:report_detail", report.pk)
        return super().dispatch(request, *args, **kwargs)


class FeedbackListView(GHDIListView):
    model = FeedbackCase
    permission_required = "monitoring.view_feedbackcase"
    search_fields = ("reference", "details")
    title = "Community Feedback"
    template_name = "monitoring/feedback_list.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("project", "created_by")
        status = self.request.GET.get("status")
        category = self.request.GET.get("category")
        if status:
            qs = qs.filter(status=status)
        if category:
            qs = qs.filter(category=category)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = FeedbackCase.Status.choices
        context["categories"] = FeedbackCase.Category.choices
        return context


class FeedbackCreateView(GHDICreateView):
    model = FeedbackCase
    form_class = FeedbackCaseForm
    permission_required = "monitoring.add_feedbackcase"
    template_name = "monitoring/feedback_form.html"
    title = "Record Community Feedback"


class FeedbackDetailView(GHDidDetailView):
    model = FeedbackCase
    permission_required = "monitoring.view_feedbackcase"
    template_name = "monitoring/feedback_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = FeedbackReviewForm(instance=self.object)
        form.fields["status"].choices = [
            choice for choice in FeedbackCase.Status.choices
            if choice[0] in FEEDBACK_TRANSITIONS.get(self.object.status, set())
        ]
        if form.fields["status"].choices:
            form.initial["status"] = form.fields["status"].choices[0][0]
        context["review_form"] = form
        return context


@login_required
@permission_required("monitoring.manage_feedbackcase", raise_exception=True)
@require_POST
def feedback_review(request, pk):
    case = get_object_or_404(FeedbackCase, pk=pk)
    form = FeedbackReviewForm(request.POST, instance=case)
    if form.is_valid() and form.cleaned_data["status"] in FEEDBACK_TRANSITIONS.get(case.status, set()):
        updated = form.save()
        log_action(request.user, "feedback_case_updated", module="monitoring", model="feedbackcase",
                   object_id=updated.pk, object_repr=updated.reference, request=request)
        if case.created_by_id and case.created_by_id != request.user.id:
            notify(case.created_by, "meal", f"Feedback case {updated.reference} updated",
                   f"The case status is now {updated.get_status_display()}.", url=updated.get_absolute_url())
        messages.success(request, "Feedback case updated.")
    else:
        messages.error(request, "Choose a valid next status and provide a resolution note when resolving or closing a case.")
    return redirect("monitoring:feedback_detail", pk)


@login_required
@permission_required("monitoring.change_mealreport", raise_exception=True)
@require_POST
def report_review(request, pk):
    report = get_object_or_404(MEALReport, pk=pk)
    action = request.POST.get("action", "")
    if action not in {"approve", "reject"} or not report.is_pending:
        messages.error(request, "That review action is not available for this report.")
        return redirect("monitoring:report_detail", pk)
    service = WorkflowService(report, request.user)
    if action == "approve":
        service.approve(step="final", note=request.POST.get("note", ""))
        messages.success(request, "Report approved.")
    elif action == "reject":
        service.reject(note=request.POST.get("note", ""))
        messages.warning(request, "Report returned for revision.")
    return redirect("monitoring:report_detail", pk)

