"""Reporting hub: organisational reports with CSV export and print views."""
import csv

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse


def _csv_response(filename, header, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response


@login_required
def hub(request):
    can = request.user.has_perm
    reports = []
    if can("hr.view_employee"):
        reports.append(("HR Summary", reverse("reports:hr_summary"), "idcard", "Staff, leave and training overview"))
    if can("finance.view_transaction"):
        reports.append(("Financial Summary", reverse("reports:finance_summary"), "wallet", "Income, expenditure and budgets"))
    if can("programs.view_project"):
        reports.append(("Program Performance", reverse("reports:program_summary"), "layers", "Projects, activities and reach"))
    if can("beneficiaries.view_beneficiary"):
        reports.append(("Beneficiary Summary", reverse("reports:beneficiary_summary"), "users", "Reach by gender, age and location"))
    if can("monitoring.view_indicator"):
        reports.append(("Indicator Performance", reverse("reports:indicator_summary"), "target", "Target vs achievement"))
    if can("partners.view_donor"):
        reports.append(("Donor Portfolio", reverse("reports:donor_portfolio"), "handshake", "Funding by donor"))
    return render(request, "reports/hub.html", {"reports": reports, "page_title": "Reports"})


@login_required
@permission_required("hr.view_employee", raise_exception=True)
def hr_summary(request):
    from apps.hr.models import Employee, LeaveRequest, Training

    employees = Employee.objects.select_related("department")
    rows = [
        [e.employee_id, e.full_name, e.position, str(e.department or ""), e.get_employment_type_display(), str(e.hire_date or ""), e.get_status_display()]
        for e in employees
    ]
    if request.GET.get("export") == "csv":
        return _csv_response("ghdi-staff.csv", ["Employee ID", "Name", "Position", "Department", "Type", "Hire Date", "Status"], rows)
    context = {
        "page_title": "HR Summary Report",
        "total": employees.count(),
        "by_department": employees.values("department__name").annotate(total=Count("id")),
        "by_type": employees.values("employment_type").annotate(total=Count("id")),
        "leave_rows": LeaveRequest.objects.select_related("employee", "leave_type")[:100],
        "trainings": Training.objects.prefetch_related("participants")[:20],
        "rows": rows,
    }
    return render(request, "reports/hr_summary.html", context)


@login_required
@permission_required("finance.view_transaction", raise_exception=True)
def finance_summary(request):
    from apps.finance.models import Budget, Transaction

    income = Transaction.objects.filter(direction="income", status__in=["approved", "completed"]).aggregate(t=Sum("amount"))["t"] or 0
    expense = Transaction.objects.filter(direction="expense", status__in=["approved", "completed"]).aggregate(t=Sum("amount"))["t"] or 0
    rows = [
        [t.reference, str(t.date), t.description, t.get_direction_display(), str(t.amount), str(t.account or ""), str(t.project or ""), t.get_status_display()]
        for t in Transaction.objects.select_related("account", "project")[:500]
    ]
    if request.GET.get("export") == "csv":
        return _csv_response("ghdi-transactions.csv", ["Reference", "Date", "Description", "Direction", "Amount", "Account", "Project", "Status"], rows)
    context = {
        "page_title": "Financial Summary Report",
        "income": income, "expense": expense, "balance": income - expense,
        "budgets": Budget.objects.filter(status="approved").prefetch_related("lines"),
        "by_category": Transaction.objects.filter(direction="expense").values("category").annotate(total=Sum("amount")),
        "rows": rows,
    }
    return render(request, "reports/finance_summary.html", context)


@login_required
@permission_required("programs.view_project", raise_exception=True)
def program_summary(request):
    from apps.programs.models import Activity, Program, Project

    rows = [
        [p.code, p.name, str(p.program), str(p.donor or ""), str(p.budget), str(p.spent), p.completion, p.get_status_display()]
        for p in Project.objects.select_related("program", "donor")
    ]
    if request.GET.get("export") == "csv":
        return _csv_response("ghdi-projects.csv", ["Code", "Project", "Program", "Donor", "Budget", "Spent", "Completion %", "Status"], rows)
    context = {
        "page_title": "Program Performance Report",
        "programs": Program.objects.prefetch_related("projects"),
        "activity_counts": Activity.objects.values("status").annotate(total=Count("id")),
        "rows": rows,
    }
    return render(request, "reports/program_summary.html", context)


@login_required
@permission_required("beneficiaries.view_beneficiary", raise_exception=True)
def beneficiary_summary(request):
    from apps.beneficiaries.models import Beneficiary

    rows = [
        [b.code, b.gender, b.age_group, b.vulnerability_category, str(b.location or ""), str(b.project or "")]
        for b in Beneficiary.objects.select_related("location", "project")[:1000]
    ]
    if request.GET.get("export") == "csv":
        return _csv_response("ghdi-beneficiaries.csv", ["Code", "Gender", "Age Group", "Category", "Location", "Project"], rows)
    context = {
        "page_title": "Beneficiary Summary Report",
        "total": Beneficiary.objects.count(),
        "by_gender": Beneficiary.objects.values("gender").annotate(total=Count("id")),
        "by_age": Beneficiary.objects.values("age_group").annotate(total=Count("id")),
        "by_category": Beneficiary.objects.values("vulnerability_category").annotate(total=Count("id")),
        "by_lga": Beneficiary.objects.values("location__lga").annotate(total=Count("id")).order_by("-total"),
        "rows": rows,
    }
    return render(request, "reports/beneficiary_summary.html", context)


@login_required
@permission_required("monitoring.view_indicator", raise_exception=True)
def indicator_summary(request):
    from apps.monitoring.models import Indicator

    indicators = Indicator.objects.select_related("program", "project")
    rows = [[i.code, i.name, str(i.target), str(i.current), i.achievement, i.unit] for i in indicators]
    if request.GET.get("export") == "csv":
        return _csv_response("ghdi-indicators.csv", ["Code", "Indicator", "Target", "Current", "Achievement %", "Unit"], rows)
    context = {"page_title": "Indicator Performance Report", "indicators": indicators, "rows": rows}
    return render(request, "reports/indicator_summary.html", context)


@login_required
@permission_required("partners.view_donor", raise_exception=True)
def donor_portfolio(request):
    from apps.partners.models import Donor

    donors = Donor.objects.prefetch_related("grants", "projects")
    rows = [
        [d.name, d.get_donor_type_display(), str(d.total_funding), str(d.funds_received), str(d.funds_spent), d.grants.count()]
        for d in donors
    ]
    if request.GET.get("export") == "csv":
        return _csv_response("ghdi-donors.csv", ["Donor", "Type", "Committed", "Received", "Spent", "Grants"], rows)
    context = {"page_title": "Donor Portfolio Report", "donors": donors, "rows": rows}
    return render(request, "reports/donor_portfolio.html", context)


