"""Role-based dashboards with live organisational data."""
import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.models import AuditLog
from apps.beneficiaries.models import Beneficiary
from apps.collaboration.models import Meeting, Task
from apps.communications.models import Announcement
from apps.core.models import Location
from apps.documents.models import Document
from apps.finance.models import Account, Advance, Budget, ExpenseRequest, Transaction
from apps.hr.models import AttendanceRecord, Employee, HRDocument, JobApplication, LeaveRequest, Training, Vacancy
from apps.monitoring.models import FeedbackCase, Indicator, MEALReport
from apps.partners.models import Donor, Grant, Partner
from apps.procurement.models import ProcurementRequest, PurchaseOrder, Vendor
from apps.programs.models import Activity, Program, Project
from apps.risk.models import Incident, Risk


def _months(n=6):
    """Return the last n months as (label, year, month)."""
    today = timezone.localdate()
    months = []
    for i in range(n - 1, -1, -1):
        month = (today.month - i - 1) % 12 + 1
        year = today.year + (today.month - i - 1) // 12
        label = datetime.date(year, month, 1).strftime("%b")
        months.append((label, year, month))
    return months


def _monthly_finance(direction, n=6):
    data = []
    for label, year, month in _months(n):
        total = Transaction.objects.filter(
            direction=direction, date__year=year, date__month=month,
            status__in=[Transaction.Status.APPROVED, Transaction.Status.COMPLETED],
        ).aggregate(t=Sum("amount"))["t"] or 0
        data.append((label, float(total)))
    return data


def _announcement_feed():
    return Announcement.objects.filter(status=Announcement.Status.PUBLISHED).order_by("-is_pinned", "-created_at")[:4]


def _greeting(user):
    hour = timezone.localtime().hour
    name = user.first_name or user.get_full_name() or "there"
    if hour < 12:
        return f"Good morning, {name}"
    if hour < 17:
        return f"Good afternoon, {name}"
    return f"Good evening, {name}"


@login_required
def index(request):
    return redirect(request.user.get_dashboard_url())


@login_required
def admin_dashboard(request):
    """Dedicated Admin command center: system-wide KPIs and configuration.

    Only the Super Administrator role gets this view; other roles keep their own
    dedicated dashboard (e.g. Executive Director -> executive dashboard).
    """
    if not request.user.is_superuser and not request.user.role == Role.ADMIN:
        return redirect("dashboard:staff")

    from django.contrib.auth import get_user_model

    UserModel = get_user_model()
    total_users = UserModel.objects.count()
    active_users = UserModel.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users
    staff_count = Employee.objects.filter(status=Employee.Status.ACTIVE).count()
    attendance_today = AttendanceRecord.objects.filter(date=timezone.localdate()).count()
    programs = Program.objects.filter(status=Program.Status.ACTIVE).count()
    projects = Project.objects.filter(status__in=[Project.Status.ACTIVE, Project.Status.AT_RISK]).count()
    open_pr = ProcurementRequest.objects.filter(status__in=["submitted", "under_review"]).count()
    open_po = PurchaseOrder.objects.filter(status=PurchaseOrder.Status.OPEN).count()
    pending_expense = ExpenseRequest.objects.filter(status__in=["submitted", "under_review"]).count()
    pending_leave = LeaveRequest.objects.filter(status__in=["submitted", "under_review"]).count()
    meal_reports_pending = MEALReport.objects.filter(status__in=["submitted", "under_review"]).count()
    indicators_below_target = Indicator.objects.filter(target__gt=0, current__lt=F("target") * Decimal("0.7")).count()
    pending_approvals = open_pr + open_po + pending_expense + pending_leave
    open_tasks = Task.objects.filter(status__in=["open", "in_progress"]).exclude(due_date__lt=timezone.localdate()).count()
    unread_notifications = 0
    try:
        from apps.notifications.models import Notification
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False).count()
    except Exception:
        pass

    year = timezone.localdate().year
    income = Transaction.objects.filter(direction="income", status__in=["approved", "completed"], created_at__year=year).aggregate(t=Sum("amount"))["t"] or 0
    expenditure = Transaction.objects.filter(direction="expense", status__in=["approved", "completed"], created_at__year=year).aggregate(t=Sum("amount"))["t"] or 0

    recent_users = UserModel.objects.order_by("-date_joined")[:8]
    recent_audit = AuditLog.objects.select_related("user").order_by("-created_at")[:10]
    expiring_projects = Project.objects.filter(
        end_date__gte=timezone.localdate(), end_date__lte=timezone.localdate() + datetime.timedelta(days=60)
    ).select_related("program")[:5]

    context = {
        "page_title": "Admin Dashboard",
        "greeting": _greeting(request.user),
        "kpis": {
            "total_users": total_users, "active_users": active_users, "inactive_users": inactive_users,
            "staff": staff_count, "programs": programs, "projects": projects,
            "pending_approvals": pending_approvals, "open_tasks": open_tasks,
            "unread_notifications": unread_notifications,
            "income": income, "expenditure": expenditure,
            "attendance_today": attendance_today, "pending_leave": pending_leave,
            "meal_reports_pending": meal_reports_pending, "indicators_below_target": indicators_below_target,
        },
        "recent_users": recent_users,
        "recent_audit": recent_audit,
        "expiring_projects": expiring_projects,
        "announcements": _announcement_feed(),
        "open_tasks": Task.objects.filter(status__in=["open", "in_progress"]).order_by("due_date")[:6],
    }
    return render(request, "dashboard/admin.html", context)


@login_required
def executive(request):
    if not request.user.has_perm("dashboard.view_executive"):
        return redirect("dashboard:staff")

    today = timezone.localdate()
    active_programs = Program.objects.filter(status=Program.Status.ACTIVE).count()
    active_projects = Project.objects.filter(status__in=[Project.Status.ACTIVE, Project.Status.AT_RISK]).count()
    staff_count = Employee.objects.filter(status=Employee.Status.ACTIVE).count()
    beneficiaries = Beneficiary.objects.filter(is_active=True).count()
    locations = Location.objects.filter(is_active=True).count()
    donors = Donor.objects.filter(projects__isnull=False).distinct().count()
    portfolio = Grant.objects.filter(is_active=True).aggregate(t=Sum("amount"))["t"] or 0
    income = Transaction.objects.filter(direction="income", status__in=["approved", "completed"]).aggregate(t=Sum("amount"))["t"] or 0
    expenditure = Transaction.objects.filter(direction="expense", status__in=["approved", "completed"]).aggregate(t=Sum("amount"))["t"] or 0
    balance = income - expenditure

    pending_txn = Transaction.objects.filter(status__in=["submitted", "under_review"], direction="expense").count()
    pending_expense = ExpenseRequest.objects.filter(status__in=["submitted", "under_review"]).count()
    pending_procurement = ProcurementRequest.objects.filter(status__in=["submitted", "under_review"]).count()
    pending_leave = LeaveRequest.objects.filter(status__in=["submitted", "under_review"]).count()
    pending_approvals = pending_txn + pending_expense + pending_procurement + pending_leave

    expiring_projects = Project.objects.filter(
        end_date__gte=today, end_date__lte=today + datetime.timedelta(days=60)
    ).select_related("program")[:5]
    reports_due = Grant.objects.filter(next_report_due__isnull=False).order_by("next_report_due")[:5]
    high_risks = Risk.objects.exclude(status=Risk.Status.CLOSED).filter(probability__gte=3, impact__gte=3)[:5]
    critical_incidents = Incident.objects.filter(status__in=["open", "investigating"]).exclude(severity="low")[:5]

    income_trend = _monthly_finance("income")
    expense_trend = _monthly_finance("expense")
    budget_data = []
    for b in Budget.objects.filter(status=Budget.Status.APPROVED).prefetch_related("lines")[:6]:
        budget_data.append((b.name[:22], float(b.total_amount), float(b.total_actual)))
    gender_map = {"M": "Male", "F": "Female", "O": "Other"}
    gender_data = [(gender_map.get(g["gender"], g["gender"]), g["total"]) for g in Beneficiary.objects.values("gender").annotate(total=Count("id"))]
    age_map = {"child": "Children", "youth": "Youth", "adult": "Adults", "older": "Older persons"}
    age_data = [(age_map.get(a["age_group"], a["age_group"]), a["total"]) for a in Beneficiary.objects.values("age_group").annotate(total=Count("id"))]
    category_map = dict(Transaction.Category.choices)
    category_data = [
        (category_map.get(c["category"], c["category"]), float(c["total"]))
        for c in Transaction.objects.filter(direction="expense", status__in=["approved", "completed"])
        .values("category").annotate(total=Sum("amount")).order_by("-total")[:6]
    ]
    program_perf = []
    for p in Program.objects.filter(status="active").prefetch_related("projects")[:6]:
        spent = sum(pr.spent for pr in p.projects.all())
        budget = sum(pr.budget for pr in p.projects.all()) or p.budget
        util = min(100.0, float(spent) / float(budget) * 100) if budget else 0
        program_perf.append((p.title[:24], float(budget), float(spent), util))
    recent_feed = AuditLog.objects.filter(
        action__in=["create", "approve", "reject", "submit", "update"]
    ).select_related("user")[:8]

    context = {
        "page_title": "Executive Dashboard",
        "greeting": _greeting(request.user),
        "kpis": {
            "active_programs": active_programs, "active_projects": active_projects,
            "staff": staff_count, "beneficiaries": beneficiaries,
            "locations": locations, "donors": donors, "portfolio": portfolio,
            "income": income, "expenditure": expenditure, "balance": balance,
            "pending_approvals": pending_approvals,
        },
        "pending": {"txn": pending_txn, "expense": pending_expense, "procurement": pending_procurement, "leave": pending_leave},
        "expiring_projects": expiring_projects,
        "reports_due": reports_due,
        "high_risks": high_risks,
        "critical_incidents": critical_incidents,
        "income_trend": income_trend,
        "expense_trend": expense_trend,
        "budget_data": budget_data,
        "gender_data": gender_data,
        "age_data": age_data,
        "category_data": category_data,
        "program_perf": program_perf,
        "announcements": _announcement_feed(),
        "recent_feed": recent_feed,
        "open_tasks": Task.objects.filter(assigned_to=request.user).exclude(status__in=["done", "cancelled"])[:5],
    }
    return render(request, "dashboard/executive.html", context)


@login_required
def hr_dashboard(request):
    if not request.user.has_perm("hr.view_employee"):
        return redirect("dashboard:staff")

    today = timezone.localdate()
    in_30 = today + datetime.timedelta(days=30)
    in_60 = today + datetime.timedelta(days=60)
    employees = Employee.objects.filter(status=Employee.Status.ACTIVE)
    total = employees.count()
    new_this_month = Employee.objects.filter(hire_date__year=today.year, hire_date__month=today.month).count()
    on_leave = employees.filter(status=Employee.Status.ON_LEAVE).count()
    on_leave_today = LeaveRequest.objects.filter(status="approved", start_date__lte=today, end_date__gte=today).count()
    contracts_expiring = employees.filter(contract_end__gte=today, contract_end__lte=in_60).order_by("contract_end")[:6]
    staff_with_birthdays = list(employees.filter(date_of_birth__isnull=False))
    upcoming_birthdays = sorted(
        staff_with_birthdays,
        key=lambda e: ((e.date_of_birth.month, e.date_of_birth.day) < (today.month, today.day), e.date_of_birth.month, e.date_of_birth.day),
    )[:6]
    attendance_today = AttendanceRecord.objects.filter(date=today)
    documents_expiring = HRDocument.objects.filter(expires_at__gte=today, expires_at__lte=in_30).select_related("employee").order_by("expires_at")[:6]
    open_vacancies = Vacancy.objects.filter(status=Vacancy.Status.OPEN)
    applications = JobApplication.objects.values("status").annotate(total=Count("id"))
    status_map = dict(JobApplication.Status.choices)
    pipeline = [(status_map.get(a["status"], a["status"]), a["total"]) for a in applications]
    trainings = Training.objects.exclude(status=Training.Status.CANCELLED).order_by("-start_date")[:6]
    reviews_due = Employee.objects.filter(performance_reviews__isnull=True)[:6]
    pending_leave = LeaveRequest.objects.filter(status__in=["submitted", "under_review"]).select_related("employee", "leave_type")[:6]
    by_department = Department_count = (
        Employee.objects.values("department__name").annotate(total=Count("id")).order_by("-total")
    )
    by_type = employees.values("employment_type").annotate(total=Count("id"))
    type_map = dict(Employee.EmploymentType.choices)
    type_data = [(type_map.get(t["employment_type"], t["employment_type"]), t["total"]) for t in by_type]
    context = {
        "page_title": "HR Dashboard",
        "greeting": _greeting(request.user),
        "kpis": {
            "total": total, "on_leave": on_leave_today, "new_this_month": new_this_month,
            "contracts_expiring": employees.filter(contract_end__gte=today, contract_end__lte=in_60).count(),
            "open_vacancies": open_vacancies.count(),
            "applications": JobApplication.objects.count(),
            "attendance_today": attendance_today.filter(status__in=("present", "late", "remote")).count(),
            "documents_expiring": HRDocument.objects.filter(expires_at__gte=today, expires_at__lte=in_30).count(),
        },
        "contracts_expiring": contracts_expiring,
        "upcoming_birthdays": upcoming_birthdays,
        "open_vacancies": open_vacancies[:5],
        "pipeline": pipeline,
        "trainings": trainings,
        "pending_leave": pending_leave,
        "documents_expiring": documents_expiring,
        "department_data": [(d["department__name"] or "Unassigned", d["total"]) for d in Department_count],
        "type_data": type_data,
        "announcements": _announcement_feed(),
    }
    return render(request, "dashboard/hr.html", context)


@login_required
def program_dashboard(request):
    if not request.user.has_perm("programs.view_project"):
        return redirect("dashboard:staff")

    today = timezone.localdate()
    is_manager = Q(manager=request.user)
    projects = Project.objects.filter(is_manager).select_related("program", "donor") or Project.objects.none()
    if request.user.has_perm("programs.add_program"):
        projects = Project.objects.exclude(status="cancelled").select_related("program", "donor")
    activities = Activity.objects.filter(project__in=projects).select_related("project", "location", "responsible")
    upcoming = activities.filter(status__in=["planned", "approved", "in_progress"], start_date__gte=today).order_by("start_date")[:6]
    delayed = [a for a in activities if a.is_delayed][:6]
    completed_count = activities.filter(status="completed").count()
    beneficiaries = Beneficiary.objects.filter(project__in=projects).count()
    budget = sum(p.budget for p in projects)
    spent = sum(p.spent for p in projects)
    indicators = Indicator.objects.filter(project__in=projects)
    below = [i for i in indicators.select_related("project") if i.is_below_target][:6]
    at_risk = projects.filter(status=Project.Status.AT_RISK)[:6]
    context = {
        "page_title": "Program Dashboard",
        "greeting": _greeting(request.user),
        "kpis": {
            "projects": projects.count(),
            "activities": activities.count(),
            "completed_activities": completed_count,
            "delayed": len(delayed),
            "beneficiaries": beneficiaries,
            "budget": budget,
            "spent": spent,
            "utilisation": min(100.0, (float(spent) / float(budget) * 100) if budget else 0),
            "indicators": indicators.count(),
        },
        "projects": projects[:8],
        "upcoming": upcoming,
        "delayed": delayed,
        "below_indicators": below,
        "at_risk": at_risk,
        "announcements": _announcement_feed(),
        "open_tasks": Task.objects.filter(assigned_to=request.user).exclude(status__in=["done", "cancelled"])[:6],
    }
    return render(request, "dashboard/program.html", context)


@login_required
def finance_dashboard(request):
    if not request.user.has_perm("finance.view_transaction"):
        return redirect("dashboard:staff")

    income = Transaction.objects.filter(direction="income", status__in=["approved", "completed"]).aggregate(t=Sum("amount"))["t"] or 0
    expenditure = Transaction.objects.filter(direction="expense", status__in=["approved", "completed"]).aggregate(t=Sum("amount"))["t"] or 0
    budgets = Budget.objects.filter(status="approved")
    total_budget = sum(b.total_amount for b in budgets)
    total_actual = sum(b.total_actual for b in budgets)
    pending_txn = Transaction.objects.filter(status__in=["submitted", "under_review"], direction="expense").select_related("account", "project")[:6]
    pending_payments = ExpenseRequest.objects.filter(status__in=["submitted", "under_review", "approved"]).select_related("requested_by")[:6]
    advances_total = Advance.objects.exclude(status=Advance.Status.RETIRED).aggregate(
        t=Sum("amount") - Sum("retired_amount")
    )["t"]
    advances = Advance.objects.exclude(status=Advance.Status.RETIRED).select_related("employee")[:6]
    expense_trend = _monthly_finance("expense")
    income_trend = _monthly_finance("income")
    category_map = dict(Transaction.Category.choices)
    category_data = [
        (category_map.get(c["category"], c["category"]), float(c["total"]))
        for c in Transaction.objects.filter(direction="expense", status__in=["approved", "completed"])
        .values("category").annotate(total=Sum("amount")).order_by("-total")
    ]
    project_spend = [
        (p.name[:22], float(p.spent))
        for p in Project.objects.exclude(budget=0).order_by("-budget")[:6]
    ]
    donor_funding = [
        (d.name[:20], float(d.funds_received))
        for d in Donor.objects.all()[:8] if d.funds_received
    ]
    budget_rows = [
        {"budget": b, "amount": float(b.total_amount), "actual": float(b.total_actual)}
        for b in budgets.prefetch_related("lines")[:6]
    ]
    context = {
        "page_title": "Finance Dashboard",
        "greeting": _greeting(request.user),
        "kpis": {
            "income": income, "expenditure": expenditure, "balance": income - expenditure,
            "total_budget": total_budget, "total_actual": total_actual,
            "utilisation": min(100.0, (total_actual / total_budget * 100) if total_budget else 0),
            "pending_payments": ExpenseRequest.objects.filter(status__in=["submitted", "under_review", "approved"]).count(),
            "pending_approvals": Transaction.objects.filter(status__in=["submitted", "under_review"]).count(),
            "advances_outstanding": float(advances_total or 0),
        },
        "pending_txn": pending_txn,
        "pending_payments": pending_payments,
        "advances": advances,
        "expense_trend": expense_trend,
        "income_trend": income_trend,
        "category_data": category_data,
        "project_spend": project_spend,
        "donor_funding": donor_funding,
        "budget_rows": budget_rows,
        "announcements": _announcement_feed(),
    }
    return render(request, "dashboard/finance.html", context)


@login_required
def meal_dashboard(request):
    if not request.user.has_perm("monitoring.view_indicator"):
        return redirect("dashboard:staff")

    indicators = Indicator.objects.select_related("program", "project")
    below = [i for i in indicators if i.is_below_target][:8]
    achievements = [(i.code, i.achievement) for i in indicators[:10]]
    by_lga = list(
        Beneficiary.objects.values("location__lga").annotate(total=Count("id")).order_by("-total")[:8]
    )
    pending_reports = MEALReport.objects.filter(status__in=["submitted", "under_review"]).select_related("project")[:6]
    recent_reports = MEALReport.objects.exclude(status="draft").select_related("project")[:6]
    feedback_pending = None
    if request.user.has_perm("monitoring.view_feedbackcase"):
        feedback_pending = FeedbackCase.objects.filter(status__in=["received", "under_review", "referred"]).count()
    context = {
        "page_title": "MEAL Dashboard",
        "greeting": _greeting(request.user),
        "kpis": {
            "indicators": indicators.count(),
            "below_target": sum(1 for i in indicators if i.is_below_target),
            "avg_achievement": round(indicators.aggregate(a=Avg("current")).get("a") or 0),
            "beneficiaries": Beneficiary.objects.filter(is_active=True).count(),
            "reports": MEALReport.objects.count(),
            "pending_reports": pending_reports.count(),
            "feedback_pending": feedback_pending,
        },
        "below": below,
        "achievements": achievements,
        "by_lga": [(r["location__lga"] or "Unassigned", r["total"]) for r in by_lga],
        "pending_reports": pending_reports,
        "recent_reports": recent_reports,
        "announcements": _announcement_feed(),
    }
    return render(request, "dashboard/meal.html", context)


@login_required
def staff_dashboard(request):
    today = timezone.localdate()
    my_tasks = Task.objects.filter(assigned_to=request.user).exclude(status__in=["done", "cancelled"]).order_by("due_date")[:8]
    employee = getattr(request.user, "employee_profile", None)
    my_leave = LeaveRequest.objects.filter(employee=employee) if employee else LeaveRequest.objects.none()
    my_leave = my_leave.select_related("leave_type")[:5]
    my_meetings = Meeting.objects.filter(participants=request.user, date__gte=today).order_by("date")[:5]
    my_projects = Project.objects.filter(manager=request.user)[:5]
    documents = Document.objects.filter(access_level="staff").order_by("-created_at")[:5]
    context = {
        "page_title": "My Dashboard",
        "greeting": _greeting(request.user),
        "my_tasks": my_tasks,
        "overdue_tasks": [t for t in my_tasks if t.is_overdue],
        "my_leave": my_leave,
        "my_meetings": my_meetings,
        "my_projects": my_projects,
        "documents": documents,
        "announcements": _announcement_feed(),
    }
    return render(request, "dashboard/staff.html", context)


@login_required
def procurement_dashboard(request):
    """Dedicated Procurement workspace: pipeline, approvals, POs and vendors."""
    if not request.user.has_perm("procurement.view_procurementrequest"):
        return redirect("dashboard:staff")

    from apps.procurement.models import ProcurementStatus

    requests = ProcurementRequest.objects.select_related("requested_by", "project", "selected_vendor")
    pipeline = [
        (ProcurementStatus.DRAFT, requests.filter(status="draft")),
        (ProcurementStatus.SUBMITTED, requests.filter(status="submitted")),
        (ProcurementStatus.UNDER_REVIEW, requests.filter(status="under_review")),
        (ProcurementStatus.APPROVED, requests.filter(status="approved")),
        (ProcurementStatus.PURCHASED, requests.filter(status="purchased")),
        (ProcurementStatus.COMPLETED, requests.filter(status="completed")),
        (ProcurementStatus.REJECTED, requests.filter(status="rejected")),
    ]
    pipeline_counts = [(s.label, q.count()) for s, q in pipeline]
    active = requests.exclude(status__in=["completed", "rejected", "cancelled", "draft"])
    pending_approvals = requests.filter(status__in=["submitted", "under_review"]).order_by("needed_by", "created_at")
    recent = requests[:8]
    purchase_orders = PurchaseOrder.objects.select_related("vendor", "request")
    open_pos = purchase_orders.filter(status=PurchaseOrder.Status.OPEN)
    max_count = max([c for _, c in pipeline_counts], default=0) or 1

    year = timezone.localdate().year
    committed = PurchaseOrder.objects.filter(order_date__year=year).aggregate(t=Sum("amount"))["t"] or 0
    estimated_value = requests.filter(created_at__year=year).aggregate(t=Sum("estimated_cost"))["t"] or 0
    top_vendors = (
        Vendor.objects.filter(is_active=True)
        .annotate(po_count=Count("purchase_orders", distinct=True))
        .order_by("-rating", "-po_count")[:6]
    )

    context = {
        "page_title": "Procurement Dashboard",
        "greeting": _greeting(request.user),
        "kpis": {
            "pending": pending_approvals.count(),
            "active": active.count(),
            "open_pos": open_pos.count(),
            "vendors": Vendor.objects.filter(is_active=True).count(),
            "committed": committed,
            "estimated_value": estimated_value,
        },
        "pipeline_counts": pipeline_counts,
        "max_count": max_count,
        "pending_approvals": pending_approvals[:6],
        "recent": recent,
        "open_pos": open_pos[:6],
        "recent_pos": purchase_orders[:6],
        "top_vendors": top_vendors,
        "announcements": _announcement_feed(),
    }
    return render(request, "dashboard/procurement.html", context)




