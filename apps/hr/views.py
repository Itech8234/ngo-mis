"""HR views: staff records, leave workflow, recruitment, training, attendance."""
import base64
import csv
from io import BytesIO
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.audit.middleware import log_action
from apps.core.generic import GHDIListView, GHDICreateView, GHDIUpdateView, GHDidDetailView
from apps.core.models import OrganizationSetting
from apps.core.services import WorkflowService, notify

from .forms import (
    AttendanceForm, DisciplinaryRecordForm, EmployeeForm, HRDocumentForm, LeaveBalanceForm, LeaveRequestForm,
    LeaveReviewForm, PerformanceReviewForm, TrainingForm, VacancyForm,
)
from .models import (
    AttendanceRecord, Department, DisciplinaryRecord, Employee, HRDocument,
    JobApplication, LeaveBalance, LeaveRequest, LeaveType, PerformanceReview,
    TimesheetEntry, Training, Vacancy,
)

User = get_user_model()


class EmployeeListView(GHDIListView):
    model = Employee
    permission_required = "hr.view_employee"
    search_fields = ("first_name", "last_name", "employee_id", "position")
    title = "Staff"
    template_name = "hr/employee_list.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("department", "supervisor")
        department = self.request.GET.get("department")
        status = self.request.GET.get("status")
        employment_type = self.request.GET.get("employment_type")
        if department:
            qs = qs.filter(department_id=department)
        if status:
            qs = qs.filter(status=status)
        if employment_type in Employee.EmploymentType.values:
            qs = qs.filter(employment_type=employment_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["departments"] = Department.objects.all()
        context["statuses"] = Employee.Status.choices
        context["employment_types"] = Employee.EmploymentType.choices
        context["selected_employment_type"] = self.request.GET.get("employment_type", "")
        return context


class EmployeeDetailView(GHDidDetailView):
    model = Employee
    permission_required = "hr.view_employee"
    template_name = "hr/employee_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object
        user = self.request.user
        show_sensitive = user.has_perm("hr.view_sensitive")
        context["show_sensitive"] = show_sensitive
        context["leave_requests"] = employee.leave_requests.all()[:10]
        context["trainings"] = employee.trainings.all()[:8]
        context["reviews"] = employee.performance_reviews.all()[:8]
        context["disciplinary"] = employee.disciplinary_records.all() if show_sensitive else []
        context["assets"] = employee.assets.all()[:10]
        context["advances"] = employee.advances.all() if user.has_perm("finance.view_advance") else []
        documents = employee.hr_documents.all()
        is_owner = employee.user_id == user.pk
        if not user.has_perm("hr.view_hrdocument") and not is_owner:
            documents = documents.none()
        elif not user.has_perm("hr.view_sensitive_hrdocument") and not is_owner:
            documents = documents.filter(is_confidential=False)
        context["hr_documents"] = documents
        return context


@login_required
@permission_required("hr.view_employee", raise_exception=True)
def employee_id_card(request, pk):
    employee = get_object_or_404(
        Employee.objects.select_related("department"), pk=pk,
    )
    import qrcode

    qr = qrcode.make(employee.employee_id)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_data = base64.b64encode(qr_buffer.getvalue()).decode("ascii")
    return render(request, "hr/id_card.html", {
        "employee": employee,
        "page_title": f"Staff ID Card — {employee.full_name}",
        "qr_data": qr_data,
    })


@login_required
@permission_required("hr.view_employee", raise_exception=True)
def employee_id_card_pdf(request, pk):
    """Create a print-ready two-sided CR80 ID card PDF on demand."""
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import landscape
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    import qrcode

    employee = get_object_or_404(Employee.objects.select_related("department"), pk=pk)
    organization = OrganizationSetting.load()
    width, height = landscape((85.6 * mm, 53.98 * mm))
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=(width, height))
    navy, magenta, gold = HexColor("#092c59"), HexColor("#a32661"), HexColor("#e8b849")
    ink, slate, pale = HexColor("#183452"), HexColor("#52657d"), HexColor("#f2f6fa")

    def draw_stored_image(field, x, y, w, h, preserve=False):
        try:
            if not field or not field.storage.exists(field.name):
                return False
            with field.open("rb") as source:
                image = ImageReader(BytesIO(source.read()))
            pdf.drawImage(image, x, y, width=w, height=h, preserveAspectRatio=preserve, anchor="c", mask="auto")
            return True
        except (OSError, ValueError):
            return False

    def draw_fitted(text, x, y, max_width, font="Helvetica-Bold", size=9, minimum=6):
        text = str(text or "")
        while size > minimum and pdf.stringWidth(text, font, size) > max_width:
            size -= 0.25
        pdf.setFont(font, size)
        pdf.drawString(x, y, text)

    # Front: premium navy, magenta and gold brand treatment with a staff-ID-only QR.
    pdf.setFillColor(pale)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#e7eff7"))
    pdf.circle(width + 2 * mm, 8 * mm, 24 * mm, fill=1, stroke=0)
    pdf.setFillColor(navy)
    pdf.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
    pdf.setFillColor(magenta)
    pdf.rect(0, height - 9 * mm, 2.4 * mm, 9 * mm, fill=1, stroke=0)
    pdf.setFillColor(gold)
    pdf.rect(2.4 * mm, height - 9 * mm, 0.7 * mm, 9 * mm, fill=1, stroke=0)
    if not draw_stored_image(getattr(organization, "logo", None), 4 * mm, height - 8 * mm, 9 * mm, 7 * mm, True):
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(4 * mm, height - 6.4 * mm, "GHDI")
    pdf.setFillColor(white)
    draw_fitted(getattr(organization, "name", "GHDI"), 15 * mm, height - 5.8 * mm, width - 40 * mm, size=7, minimum=5.5)
    pdf.setFillColor(HexColor("#dce5ef"))
    pdf.setFont("Helvetica-Bold", 5.5)
    pdf.drawRightString(width - 4 * mm, height - 5.8 * mm, "STAFF IDENTITY")

    # Portrait with a crisp white mat.
    photo_x, photo_y, photo_w, photo_h = 5 * mm, 15 * mm, 22 * mm, 27 * mm
    pdf.setFillColor(white)
    pdf.roundRect(photo_x - 0.8 * mm, photo_y - 0.8 * mm, photo_w + 1.6 * mm, photo_h + 1.6 * mm, 2 * mm, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#dce7f1"))
    pdf.roundRect(photo_x, photo_y, photo_w, photo_h, 1.5 * mm, fill=1, stroke=0)
    if not draw_stored_image(employee.photo, photo_x, photo_y, photo_w, photo_h):
        pdf.setFillColor(navy)
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2 - 2 * mm,
                              (employee.first_name[:1] + employee.last_name[:1]).upper())

    text_x = 31 * mm
    text_width = width - text_x - 20 * mm
    pdf.setFillColor(ink)
    draw_fitted(employee.full_name, text_x, height - 17 * mm, text_width, size=10, minimum=7)
    pdf.setFillColor(magenta)
    draw_fitted(employee.position, text_x, height - 22 * mm, text_width, font="Helvetica-Bold", size=7.2, minimum=5.5)
    pdf.setStrokeColor(gold)
    pdf.setLineWidth(0.6)
    pdf.line(text_x, height - 24 * mm, min(width - 5 * mm, text_x + 36 * mm), height - 24 * mm)
    pdf.setFillColor(slate)
    pdf.setFont("Helvetica-Bold", 5.3)
    pdf.drawString(text_x, height - 28 * mm, "DEPARTMENT")
    draw_fitted(employee.department.name if employee.department else "To be assigned", text_x, height - 31 * mm, text_width, font="Helvetica", size=6.5, minimum=5.3)
    pdf.setFont("Helvetica-Bold", 5.3)
    pdf.drawString(text_x, height - 35 * mm, "EMPLOYMENT")
    employment = f"Since {employee.hire_date:%d %b %Y}" if employee.hire_date else "Date not recorded"
    draw_fitted(employment, text_x, height - 38 * mm, text_width, font="Helvetica", size=6.2, minimum=5.2)

    # Bottom credential strip.
    pdf.setFillColor(navy)
    pdf.roundRect(30 * mm, 4 * mm, width - 35 * mm, 7 * mm, 1.2 * mm, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 6.3)
    pdf.drawString(33 * mm, 6.4 * mm, employee.employee_id)
    validity = f"VALID THROUGH {employee.contract_end:%d %b %Y}" if employee.contract_end else "VALID WHILE EMPLOYED"
    pdf.setFillColor(HexColor("#e8edf4"))
    pdf.setFont("Helvetica-Bold", 4.6)
    pdf.drawRightString(width - 8 * mm, 6.5 * mm, validity)
    qr = qrcode.make(employee.employee_id)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    pdf.drawImage(ImageReader(BytesIO(qr_buffer.getvalue())), width - 16 * mm, 14 * mm, 10 * mm, 10 * mm)
    pdf.showPage()

    # Back: secure return instructions and organizational contact details.
    pdf.setFillColor(navy)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#123d69"))
    pdf.circle(width + 4 * mm, 3 * mm, 30 * mm, fill=1, stroke=0)
    pdf.setFillColor(magenta)
    pdf.rect(0, height - 9 * mm, width, 9 * mm, fill=1, stroke=0)
    pdf.setFillColor(gold)
    pdf.rect(0, 0, width, 2 * mm, fill=1, stroke=0)
    pdf.setFillColor(white)
    draw_fitted(getattr(organization, "name", "Garkuwa Humanitarian and Development Initiative"), 6 * mm, height - 5.8 * mm, width - 12 * mm, size=7, minimum=5.5)
    pdf.setFillColor(HexColor("#f4d27b"))
    pdf.setFont("Helvetica-Bold", 5.4)
    pdf.drawString(7 * mm, height - 16 * mm, "IF FOUND, PLEASE RETURN THIS CARD")
    pdf.setFillColor(HexColor("#e1eaf4"))
    pdf.setFont("Helvetica", 6.6)
    pdf.drawString(7 * mm, height - 21 * mm, "This card confirms organizational affiliation only.")
    pdf.drawString(7 * mm, height - 25 * mm, "It does not grant access to restricted premises or information.")
    if getattr(organization, "phone", ""):
        draw_fitted(f"Telephone: {organization.phone}", 7 * mm, height - 29 * mm, 50 * mm, font="Helvetica", size=6.2, minimum=5)
    if getattr(organization, "email", ""):
        draw_fitted(f"Email: {organization.email}", 7 * mm, height - 33 * mm, 50 * mm, font="Helvetica", size=6.2, minimum=5)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawString(7 * mm, 6 * mm, employee.employee_id)
    pdf.setFont("Helvetica", 5.3)
    pdf.setFillColor(HexColor("#d3deea"))
    pdf.drawString(7 * mm, 3.7 * mm, "Staff identification")
    qr = qrcode.make(employee.employee_id)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    pdf.drawImage(ImageReader(BytesIO(qr_buffer.getvalue())), width - 21 * mm, 8 * mm, 15 * mm, 15 * mm)
    pdf.save()

    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{employee.employee_id}-ID-card.pdf"'
    log_action(request.user, "employee_id_card_exported", module="hr", object_id=employee.pk,
               object_repr=employee.employee_id, request=request)
    return response


class EmployeeCreateView(GHDICreateView):
    model = Employee
    form_class = EmployeeForm
    permission_required = "hr.add_employee"
    template_name = "hr/employee_form.html"
    title = "Add Staff Member"


class EmployeeUpdateView(GHDIUpdateView):
    model = Employee
    form_class = EmployeeForm
    permission_required = "hr.change_employee"
    template_name = "hr/employee_form.html"
    title = "Edit Staff Member"


class LeaveListView(GHDIListView):
    model = LeaveRequest
    permission_required = "hr.view_leaverequest"
    search_fields = ("employee__first_name", "employee__last_name", "reason")
    title = "Leave Requests"

    def get_queryset(self):
        qs = super().get_queryset().select_related("employee", "leave_type", "submitted_by")
        status = self.request.GET.get("status")
        if self.request.user.has_perm("hr.approve_leave") or self.request.user.has_perm("hr.view_employee"):
            pass  # HR / approvers see all
        else:
            employee = getattr(self.request.user, "employee_profile", None)
            qs = qs.filter(employee=employee) if employee else qs.none()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = [("submitted", "Submitted"), ("under_review", "Under Review"), ("approved", "Approved"), ("rejected", "Rejected"), ("cancelled", "Cancelled"), ("completed", "Completed"), ("draft", "Draft")]
        return context


class LeaveDetailView(GHDidDetailView):
    model = LeaveRequest
    permission_required = "hr.view_leaverequest"
    template_name = "hr/leave_detail.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("employee", "leave_type")
        if self.request.user.has_perm("hr.approve_leave") or self.request.user.has_perm("hr.view_employee"):
            return qs
        employee = getattr(self.request.user, "employee_profile", None)
        return qs.filter(employee=employee) if employee else qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["review_form"] = LeaveReviewForm()
        context["can_review"] = self.request.user.has_perm("hr.approve_leave")
        context["leave_balance"] = LeaveBalance.objects.filter(employee=self.object.employee, leave_type=self.object.leave_type, year=self.object.start_date.year).first()
        return context


class LeaveCreateView(GHDICreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm
    permission_required = "hr.add_leaverequest"
    template_name = "hr/leave_form.html"
    title = "Request Leave"

    def form_valid(self, form):
        employee = getattr(self.request.user, "employee_profile", None)
        if not employee:
            messages.error(self.request, "No staff profile is linked to your account. Contact HR.")
            return redirect("hr:leave_list")
        form.instance.employee = employee
        response = super().form_valid(form)
        # Notify supervisor and HR officers
        reviewers = []
        if employee.supervisor and employee.supervisor.user:
            reviewers.append(employee.supervisor.user)
        reviewers.extend(User.objects.filter(role="hr", is_active=True))
        WorkflowService(self.object, self.request.user).submit(
            notify_users=reviewers, step="supervisor",
        )
        messages.success(self.request, "Leave request submitted for review.")
        return response


@login_required
@permission_required("hr.approve_leave", raise_exception=True)
@require_POST
def leave_review(request, pk):
    """Supervisor review (-> under_review) and final HR approval/rejection."""
    leave = get_object_or_404(LeaveRequest, pk=pk)
    action = request.POST.get("action", "")
    note = request.POST.get("note", "")
    service = WorkflowService(leave, request.user)
    if action == "review" and leave.status == "submitted":
        service.review(step="supervisor", note=note)
        leave.hr_reviewed_at = None
        messages.success(request, "Leave request moved to HR review.")
        # Notify HR officers
        notify(
            leave.employee.user, "hr", "Leave request progressing",
            f"Your leave request “{leave}” was reviewed by your supervisor.",
            url=leave.get_absolute_url(),
        ) if leave.employee.user else None
    elif action == "approve":
        service.approve(step="final", note=note)
        employee = leave.employee
        employee.status = Employee.Status.ON_LEAVE if leave.start_date <= timezone.localdate() <= leave.end_date else employee.status
        employee.save(update_fields=["status", "updated_at"])
        messages.success(request, "Leave approved.")
    elif action == "reject":
        service.reject(note=note)
        messages.warning(request, "Leave request rejected.")
    elif action == "cancel":
        service.cancel(note=note)
        messages.info(request, "Leave request cancelled.")
    return redirect("hr:leave_detail", pk)


class VacancyListView(GHDIListView):
    model = Vacancy
    permission_required = "hr.view_vacancy"
    search_fields = ("title", "description")
    title = "Recruitment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["applications_by_status"] = (
            JobApplication.objects.values("status").annotate(total=Count("id")).order_by("status")
        )
        context["recent_applications"] = JobApplication.objects.select_related("vacancy")[:8]
        return context


class VacancyDetailView(GHDidDetailView):
    model = Vacancy
    permission_required = "hr.view_vacancy"
    template_name = "hr/vacancy_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["applications"] = self.object.applications.all().order_by("-created_at")
        return context


class VacancyCreateView(GHDICreateView):
    model = Vacancy
    form_class = VacancyForm
    permission_required = "hr.add_vacancy"
    template_name = "hr/vacancy_form.html"
    title = "Post Vacancy"


class VacancyUpdateView(GHDIUpdateView):
    model = Vacancy
    form_class = VacancyForm
    permission_required = "hr.change_vacancy"
    template_name = "hr/vacancy_form.html"
    title = "Edit Vacancy"


@login_required
@permission_required("hr.change_jobapplication", raise_exception=True)
@require_POST
def application_update_status(request, pk):
    application = get_object_or_404(JobApplication, pk=pk)
    new_status = request.POST.get("status")
    interview_date = request.POST.get("interview_date")
    if new_status in JobApplication.Status.values:
        old = application.status
        application.status = new_status
        if interview_date:
            from django.utils.dateparse import parse_datetime

            application.interview_date = parse_datetime(interview_date) or application.interview_date
        application.save(update_fields=["status", "interview_date", "updated_at"])
        log_action(
            request.user, "update", module="hr", model="jobapplication",
            object_id=application.pk, object_repr=str(application),
            changes={"status": {"from": old, "to": new_status}}, request=request,
        )
        messages.success(request, "Application updated.")
    return redirect("hr:vacancy_detail", application.vacancy_id)


class TrainingListView(GHDIListView):
    model = Training
    permission_required = "hr.view_training"
    search_fields = ("title", "provider", "category")
    title = "Training & Capacity Building"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("participants")


class TrainingDetailView(GHDidDetailView):
    model = Training
    permission_required = "hr.view_training"
    template_name = "hr/training_detail.html"


class TrainingCreateView(GHDICreateView):
    model = Training
    form_class = TrainingForm
    permission_required = "hr.add_training"
    template_name = "hr/training_form.html"
    title = "Plan Training"


class TrainingUpdateView(GHDIUpdateView):
    model = Training
    form_class = TrainingForm
    permission_required = "hr.change_training"
    template_name = "hr/training_form.html"
    title = "Edit Training"


@login_required
@permission_required("hr.view_attendancerecord", raise_exception=True)
def attendance_list(request):
    qs = _attendance_queryset(request)
    page = Paginator(qs, 50).get_page(request.GET.get("page"))
    today_records = AttendanceRecord.objects.filter(date=timezone.localdate())
    return render(request, "hr/attendance_list.html", {
        "records": page, "page_obj": page, "page_title": "Attendance",
        "statuses": AttendanceRecord.Status.choices,
        "departments": Department.objects.all(),
        "employees": Employee.objects.filter(status=Employee.Status.ACTIVE).order_by("first_name", "last_name"),
        "selected": {key: request.GET.get(key, "") for key in ("date_from", "date_to", "status", "department", "employee")},
        "today_count": today_records.count(),
        "present_today": today_records.filter(status__in=("present", "late", "remote")).count(),
        "today_date": timezone.localdate(),
    })


def _attendance_queryset(request):
    qs = AttendanceRecord.objects.select_related("employee", "employee__department").order_by("-date", "employee__last_name")
    date_from, date_to = parse_date(request.GET.get("date_from", "")), parse_date(request.GET.get("date_to", ""))
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    status = request.GET.get("status", "")
    if status in AttendanceRecord.Status.values:
        qs = qs.filter(status=status)
    employee = request.GET.get("employee", "")
    if employee.isdigit():
        qs = qs.filter(employee_id=employee)
    department = request.GET.get("department", "").strip()
    if department.isdigit():
        qs = qs.filter(employee__department_id=department)
    return qs


def _safe_csv_cell(value):
    text = str(value or "")
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@login_required
@permission_required("hr.view_attendancerecord", raise_exception=True)
def attendance_export(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="ghdi-attendance.csv"'
    writer = csv.writer(response)
    writer.writerow(("Staff ID", "Staff member", "Department", "Date", "Status", "Check in", "Check out", "Note"))
    for row in _attendance_queryset(request).iterator():
        writer.writerow(tuple(_safe_csv_cell(value) for value in (row.employee.employee_id, row.employee.full_name, row.employee.department or "", row.date, row.get_status_display(), row.check_in or "", row.check_out or "", row.note)))
    log_action(request.user, "attendance_exported", module="hr", request=request)
    return response


@login_required
@permission_required("hr.add_attendancerecord", raise_exception=True)
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    # New attendance entries always belong to today; HR can use the correction
    # screen to amend a date later if they are entering a historical record.
    form.fields.pop("date")
    if request.method == "POST" and form.is_valid():
        attendance_date = timezone.localdate()
        if AttendanceRecord.objects.filter(
            employee=form.cleaned_data["employee"], date=attendance_date
        ).exists():
            form.add_error("employee", "Attendance is already recorded for this staff member today. Use Correct attendance to update it.")
        else:
            form.instance.date = attendance_date
            record = form.save()
            log_action(request.user, "create", module="hr", model="attendancerecord", object_id=record.pk, object_repr=str(record), request=request)
            messages.success(request, "Attendance recorded.")
            return redirect("hr:attendance_list")
    return render(request, "hr/attendance_form.html", {
        "form": form,
        "page_title": "Record Attendance",
        "today_date": timezone.localdate(),
    })


@login_required
@permission_required("hr.change_attendancerecord", raise_exception=True)
def attendance_edit(request, pk):
    record = get_object_or_404(AttendanceRecord.objects.select_related("employee"), pk=pk)
    form = AttendanceForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        old = {"status": record.status, "check_in": str(record.check_in or ""), "check_out": str(record.check_out or "")}
        record = form.save()
        log_action(request.user, "update", module="hr", model="attendancerecord", object_id=record.pk, object_repr=str(record), changes={"before": old, "after": {"status": record.status, "check_in": str(record.check_in or ""), "check_out": str(record.check_out or "")}}, request=request)
        messages.success(request, "Attendance record updated.")
        return redirect("hr:attendance_list")
    return render(request, "hr/attendance_form.html", {"form": form, "page_title": "Correct Attendance"})


@login_required
@permission_required("hr.clock_attendance", raise_exception=True)
@require_POST
def attendance_clock(request, action):
    if action not in ("in", "out"):
        return HttpResponse(status=400)
    employee = getattr(request.user, "employee_profile", None)
    if not employee:
        messages.error(request, "Your account is not linked to a staff record. Contact HR.")
        return redirect("dashboard:staff")
    now = timezone.localtime()
    if action == "out" and not AttendanceRecord.objects.filter(employee=employee, date=timezone.localdate(), check_in__isnull=False).exists():
        messages.error(request, "Clock in before clocking out.")
        return redirect("hr:my_attendance")
    record, _ = AttendanceRecord.objects.get_or_create(employee=employee, date=timezone.localdate(), defaults={"status": AttendanceRecord.Status.PRESENT})
    if action == "in":
        if record.check_in:
            messages.info(request, "You have already clocked in today.")
        else:
            record.check_in = now.time().replace(microsecond=0)
            record.status = AttendanceRecord.Status.PRESENT
            record.save(update_fields=("check_in", "status"))
            log_action(request.user, "attendance_clock_in", module="hr", object_id=record.pk, request=request)
            messages.success(request, f"Clocked in at {record.check_in:%H:%M}.")
    elif action == "out":
        if not record.check_in:
            messages.error(request, "Clock in before clocking out.")
        elif record.check_out:
            messages.info(request, "You have already clocked out today.")
        else:
            record.check_out = now.time().replace(microsecond=0)
            record.save(update_fields=("check_out",))
            log_action(request.user, "attendance_clock_out", module="hr", object_id=record.pk, request=request)
            messages.success(request, f"Clocked out at {record.check_out:%H:%M}.")
    else:
        return HttpResponse(status=400)
    return redirect("hr:my_attendance")


@login_required
def my_attendance(request):
    employee = getattr(request.user, "employee_profile", None)
    if not employee:
        messages.error(request, "Your account is not linked to a staff record.")
        return redirect("dashboard:staff")
    qs = AttendanceRecord.objects.filter(employee=employee).order_by("-date")
    if request.GET.get("month", "").isdigit():
        month = int(request.GET["month"])
        if 1 <= month <= 12:
            qs = qs.filter(date__year=timezone.localdate().year, date__month=month)
    records = Paginator(qs, 30).get_page(request.GET.get("page"))
    today = AttendanceRecord.objects.filter(employee=employee, date=timezone.localdate()).first()
    return render(request, "hr/my_attendance.html", {"employee": employee, "records": records, "today": today, "selected_month": request.GET.get("month", ""), "page_title": "My Attendance"})


@login_required
@permission_required("hr.add_hrdocument", raise_exception=True)
def employee_document_upload(request, employee_pk):
    employee = get_object_or_404(Employee, pk=employee_pk)
    form = HRDocumentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        document = form.save(commit=False)
        document.employee = employee
        document.uploaded_by = request.user
        document.created_by = request.user
        document.updated_by = request.user
        document.save()
        log_action(request.user, "create", module="hr", model="hrdocument", object_id=document.pk, object_repr=str(document), request=request)
        messages.success(request, "Personnel document uploaded to the private HR file store.")
        return redirect("hr:employee_detail", employee.pk)
    return render(request, "hr/document_form.html", {"form": form, "employee": employee, "page_title": "Upload HR Document"})


@login_required
@permission_required("hr.view_hrdocument", raise_exception=True)
def hr_document_list(request):
    qs = HRDocument.objects.select_related("employee", "employee__department").order_by("expires_at", "employee__last_name")
    if not request.user.has_perm("hr.view_sensitive_hrdocument"):
        qs = qs.filter(is_confidential=False)
    doc_type = request.GET.get("type", "")
    verification = request.GET.get("verification", "")
    if doc_type in HRDocument.DocumentType.values:
        qs = qs.filter(document_type=doc_type)
    if verification in HRDocument.Verification.values:
        qs = qs.filter(verification=verification)
    if request.GET.get("expiring") == "1":
        qs = qs.filter(expires_at__gte=timezone.localdate(), expires_at__lte=timezone.localdate() + timezone.timedelta(days=60))
    page = Paginator(qs, 40).get_page(request.GET.get("page"))
    return render(request, "hr/document_list.html", {"documents": page, "page_obj": page, "page_title": "Personnel Documents", "types": HRDocument.DocumentType.choices, "verifications": HRDocument.Verification.choices})


@login_required
def employee_document_download(request, pk):
    document = get_object_or_404(HRDocument.objects.select_related("employee"), pk=pk)
    own = document.employee.user_id == request.user.pk
    if not (own or request.user.has_perm("hr.view_hrdocument")):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    if document.is_confidential and not (own or request.user.has_perm("hr.view_sensitive_hrdocument")):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    try:
        source = document.file.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("The stored document is unavailable.")
    log_action(request.user, "download", module="hr", model="hrdocument", object_id=document.pk, object_repr=str(document), request=request)
    response = FileResponse(source, as_attachment=True, filename=Path(document.file.name).name)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def my_documents(request):
    employee = getattr(request.user, "employee_profile", None)
    if not employee:
        messages.error(request, "Your account is not linked to an employee record.")
        return redirect("dashboard:staff")
    documents = employee.hr_documents.filter(is_confidential=False).order_by("-created_at")
    return render(request, "hr/my_documents.html", {"documents": documents, "page_title": "My HR Documents"})


@login_required
@permission_required("hr.delete_hrdocument", raise_exception=True)
@require_POST
def employee_document_delete(request, pk):
    document = get_object_or_404(HRDocument, pk=pk)
    employee_pk = document.employee_id
    name = str(document)
    document.file.delete(save=False)
    document.delete()
    log_action(request.user, "delete", module="hr", model="hrdocument", object_id=pk, object_repr=name, request=request)
    messages.success(request, "Document deleted.")
    return redirect("hr:employee_detail", employee_pk)


@login_required
@permission_required("hr.view_leavebalance", raise_exception=True)
def leave_balances(request):
    year_raw = request.GET.get("year", str(timezone.localdate().year))
    year = int(year_raw) if year_raw.isdigit() and 2000 <= int(year_raw) <= 2200 else timezone.localdate().year
    qs = LeaveBalance.objects.filter(year=year).select_related("employee", "leave_type")
    if not request.user.has_perm("hr.view_employee"):
        employee = getattr(request.user, "employee_profile", None)
        qs = qs.filter(employee=employee) if employee else qs.none()
    return render(request, "hr/leave_balances.html", {"balances": qs, "year": year, "page_title": f"Leave Balances — {year}"})


@login_required
@permission_required("hr.add_leavebalance", raise_exception=True)
def leave_balance_create(request):
    form = LeaveBalanceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        balance = form.save()
        log_action(request.user, "create", module="hr", model="leavebalance", object_id=balance.pk, object_repr=str(balance), request=request)
        messages.success(request, "Leave entitlement saved.")
        return redirect("hr:leave_balances")
    return render(request, "hr/leave_balance_form.html", {"form": form, "page_title": "Set Leave Entitlement"})


@login_required
@permission_required("hr.change_leavebalance", raise_exception=True)
def leave_balance_edit(request, pk):
    balance = get_object_or_404(LeaveBalance, pk=pk)
    form = LeaveBalanceForm(request.POST or None, instance=balance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Leave entitlement updated.")
        return redirect("hr:leave_balances")
    return render(request, "hr/leave_balance_form.html", {"form": form, "page_title": "Edit Leave Entitlement"})


@login_required
def leave_attachment_download(request, pk):
    leave = get_object_or_404(LeaveRequest.objects.select_related("employee"), pk=pk)
    own = leave.employee.user_id == request.user.pk
    if not (own or request.user.has_perm("hr.view_leaverequest")):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    if not leave.attachment:
        raise Http404("No attachment was uploaded.")
    try:
        source = leave.attachment.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("The stored attachment is unavailable.")
    log_action(request.user, "download", module="hr", model="leaverequest", object_id=leave.pk, object_repr=str(leave), request=request)
    response = FileResponse(source, as_attachment=True, filename=Path(leave.attachment.name).name)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@permission_required("hr.view_performancereview", raise_exception=True)
def performance_list(request):
    reviews = PerformanceReview.objects.select_related("employee", "reviewer").order_by("-created_at")
    return render(request, "hr/performance_list.html", {"reviews": reviews, "page_title": "Performance Appraisals"})


@login_required
@permission_required("hr.add_performancereview", raise_exception=True)
def performance_create(request):
    form = PerformanceReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.reviewer = request.user
        review.save()
        messages.success(request, "Performance review saved.")
        return redirect("hr:performance_list")
    return render(request, "hr/performance_form.html", {"form": form, "page_title": "New Performance Review"})


@login_required
@permission_required("hr.change_performancereview", raise_exception=True)
def performance_edit(request, pk):
    review = get_object_or_404(PerformanceReview, pk=pk)
    form = PerformanceReviewForm(request.POST or None, instance=review)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Performance review updated.")
        return redirect("hr:performance_list")
    return render(request, "hr/performance_form.html", {"form": form, "page_title": "Edit Performance Review"})


@login_required
@permission_required("hr.view_disciplinaryrecord", raise_exception=True)
def disciplinary_list(request):
    records = DisciplinaryRecord.objects.select_related("employee").order_by("-date")
    if not request.user.has_perm("hr.view_sensitive"):
        records = records.filter(employee__user=request.user)
    return render(request, "hr/disciplinary_list.html", {"records": records[:100], "page_title": "Disciplinary Records"})


@login_required
@permission_required("hr.add_disciplinaryrecord", raise_exception=True)
def disciplinary_create(request):
    form = DisciplinaryRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save()
        log_action(request.user, "create", module="hr", model="disciplinaryrecord", object_id=record.pk, object_repr=str(record), request=request)
        messages.success(request, "Disciplinary record saved.")
        return redirect("hr:disciplinary_list")
    return render(request, "hr/disciplinary_form.html", {"form": form, "page_title": "New Disciplinary Record"})


@login_required
@permission_required("hr.view_employee", raise_exception=True)
def orgchart(request):
    departments = Department.objects.prefetch_related("employees")
    heads = Employee.objects.filter(status=Employee.Status.ACTIVE, supervisor__isnull=True)[:12]
    return render(request, "hr/orgchart.html", {"departments": departments, "heads": heads, "page_title": "Organizational Chart"})


@login_required
@permission_required("hr.view_employee", raise_exception=True)
def directory(request):
    employees = Employee.objects.filter(status=Employee.Status.ACTIVE).select_related("department")
    query = request.GET.get("q", "").strip()
    if query:
        employees = employees.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(position__icontains=query))
    return render(request, "hr/directory.html", {"employees": employees, "query": query, "page_title": "Staff Directory"})


