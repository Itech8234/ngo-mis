# Django admin registration (customized).
from django.contrib import admin

from .models import AttendanceRecord, Employee, HRDocument, LeaveBalance, LeaveRequest


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "first_name", "last_name", "department", "position", "status")
    list_filter = ("status", "employment_type", "department")
    search_fields = ("employee_id", "first_name", "last_name", "email")


@admin.register(AttendanceRecord)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "status", "check_in", "check_out")
    list_filter = ("date", "status", "employee__department")
    date_hierarchy = "date"


@admin.register(HRDocument)
class HRDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "employee", "document_type", "verification", "expires_at", "is_confidential")
    list_filter = ("document_type", "verification", "is_confidential")
    search_fields = ("title", "employee__first_name", "employee__last_name", "employee__employee_id")


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "year", "entitled_days", "carry_forward_days")
    list_filter = ("year", "leave_type")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "days", "status")
    list_filter = ("status", "leave_type")
