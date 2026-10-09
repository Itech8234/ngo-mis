"""Role-based access control: role -> permission matrix and Django backend.

Permissions follow Django's ``app_label.action_model`` convention plus custom
actions such as ``finance.approve_payment`` and ``hr.approve_leave`` declared
on model Meta. The backend resolves permissions from this matrix so RBAC works
without duplicating Group records; superusers bypass everything.
"""
from apps.accounts.models import Role

READ_ALL = [
    "programs.view_program", "programs.view_project", "programs.view_activity",
    "beneficiaries.view_beneficiary", "monitoring.view_indicator",
    "documents.view_document", "collaboration.view_task", "collaboration.view_meeting",
    "communications.view_announcement", "reports.view_report",
]

ROLE_PERMISSIONS = {
    Role.ADMIN: ["*"],

    Role.EXEC: [
        "dashboard.view_executive",
        "hr.view_employee", "hr.view_leaverequest", "hr.approve_leave",
        "hr.view_vacancy", "hr.view_training", "hr.view_performancereview",
        "hr.view_attendancerecord", "hr.view_disciplinaryrecord",
        "programs.view_program", "programs.view_project", "programs.view_activity",
        "programs.approve_project", "programs.add_program", "programs.change_program",
        "beneficiaries.view_beneficiary", "beneficiaries.view_pii",
        "monitoring.view_indicator", "monitoring.view_mealreport",
        "finance.view_transaction", "finance.view_budget", "finance.approve_payment",
        "finance.approve_expense", "finance.view_expenserequest", "finance.view_advance",
        "finance.view_account", "finance.view_bankreconciliation",
        "partners.view_donor", "partners.view_partner", "partners.view_grant",
        "procurement.view_procurementrequest", "procurement.approve_request",
        "procurement.view_vendor", "procurement.view_purchaseorder",
        "assets.view_asset", "documents.view_document", "documents.add_document",
        "documents.view_restricted_document",
        "collaboration.view_task", "collaboration.view_meeting",
        "communications.view_announcement", "communications.add_announcement",
        "risk.view_risk", "risk.view_incident", "audit.view_auditlog",
        "reports.view_report", "accounts.export_report", "accounts.view_user",
        "core.change_organizationsetting",
    ],

    Role.MEAL: [
        "monitoring.view_indicator", "monitoring.add_indicator", "monitoring.change_indicator",
        "monitoring.view_indicatorupdate", "monitoring.add_indicatorupdate", "monitoring.change_indicatorupdate",
        "monitoring.view_mealreport", "monitoring.add_mealreport", "monitoring.change_mealreport",
        "monitoring.view_feedbackcase", "monitoring.add_feedbackcase", "monitoring.manage_feedbackcase",
        "programs.view_program", "programs.view_project", "programs.view_activity",
        "beneficiaries.view_beneficiary", "beneficiaries.view_pii",
        "beneficiaries.add_beneficiary", "beneficiaries.change_beneficiary",
        "finance.view_budget",
        "partners.view_donor", "partners.view_grant",
        "documents.view_document", "documents.add_document",
        "documents.view_restricted_document",
        "collaboration.view_task", "collaboration.view_meeting",
        "communications.view_announcement", "reports.view_report",
        "core.view_location",
    ],

    Role.HR: [
        "hr.view_department", "hr.add_department", "hr.change_department", "hr.delete_department",
        "hr.view_employee", "hr.add_employee", "hr.change_employee",
        "hr.view_sensitive", "hr.view_leaverequest", "hr.add_leaverequest",
        "hr.approve_leave", "hr.view_vacancy", "hr.add_vacancy", "hr.change_vacancy",
        "hr.view_jobapplication", "hr.add_jobapplication", "hr.change_jobapplication",
        "hr.view_training", "hr.add_training", "hr.change_training",
        "hr.view_attendancerecord", "hr.add_attendancerecord",
        "hr.change_attendancerecord", "hr.view_leavebalance", "hr.add_leavebalance",
        "hr.change_leavebalance", "hr.view_hrdocument", "hr.add_hrdocument",
        "hr.change_hrdocument", "hr.delete_hrdocument", "hr.view_sensitive_hrdocument",
        "hr.view_performancereview", "hr.add_performancereview", "hr.change_performancereview",
        "hr.view_disciplinaryrecord", "hr.add_disciplinaryrecord", "hr.change_disciplinaryrecord",
        "programs.view_project", "programs.view_program",
        "documents.view_document", "documents.add_document",
        "documents.view_restricted_document", "documents.view_confidential_document",
        "collaboration.view_task", "collaboration.view_meeting",
        "communications.view_announcement", "reports.view_report",
    ],

    Role.PM: [
        "programs.view_program", "programs.add_program", "programs.change_program",
        "programs.view_project", "programs.add_project", "programs.change_project",
        "programs.approve_project",
        "programs.view_activity", "programs.add_activity", "programs.change_activity",
        "beneficiaries.view_beneficiary", "beneficiaries.view_pii",
        "beneficiaries.add_beneficiary", "beneficiaries.change_beneficiary",
        "monitoring.view_indicator", "monitoring.add_indicator", "monitoring.change_indicator",
        "monitoring.view_indicatorupdate", "monitoring.add_indicatorupdate",
        "monitoring.view_mealreport",
        "finance.view_budget", "finance.view_transaction",
        "partners.view_donor", "partners.view_partner", "partners.view_grant",
        "documents.view_document", "documents.add_document",
        "collaboration.view_task", "collaboration.add_task", "collaboration.change_task",
        "collaboration.view_meeting", "collaboration.add_meeting", "collaboration.change_meeting",
        "communications.view_announcement", "risk.view_risk", "risk.add_risk",
        "reports.view_report", "core.view_location", "core.add_location", "core.change_location",
    ],

    Role.FIN: [
        "finance.view_transaction", "finance.add_transaction", "finance.change_transaction",
        "finance.approve_payment", "finance.view_budget", "finance.add_budget",
        "finance.change_budget", "finance.approve_budget", "finance.view_account",
        "finance.add_account", "finance.change_account", "finance.view_expenserequest",
        "finance.approve_expense", "finance.view_advance", "finance.add_advance",
        "finance.change_advance", "finance.view_bankreconciliation",
        "finance.add_bankreconciliation",
        "partners.view_donor", "partners.add_donor", "partners.change_donor",
        "partners.view_grant", "partners.add_grant", "partners.change_grant",
        "programs.view_program", "programs.view_project",
        "procurement.view_procurementrequest", "procurement.view_purchaseorder",
        "documents.view_document", "documents.add_document",
        "hr.view_employee",
        "reports.view_report", "accounts.export_report",
        "communications.view_announcement",
    ],

    Role.PROC: [
        "procurement.view_procurementrequest", "procurement.add_procurementrequest",
        "procurement.change_procurementrequest", "procurement.approve_request",
        "procurement.view_vendor", "procurement.add_vendor", "procurement.change_vendor",
        "procurement.view_quotation", "procurement.add_quotation",
        "procurement.view_purchaseorder", "procurement.add_purchaseorder",
        "procurement.change_purchaseorder",
        "assets.view_asset", "assets.add_asset", "assets.change_asset",
        "programs.view_project", "programs.view_activity",
        "finance.view_transaction",
        "documents.view_document", "documents.add_document",
        "reports.view_report", "communications.view_announcement",
    ],

    Role.STAFF: [
        "hr.clock_attendance",
        "hr.view_leaverequest", "hr.add_leaverequest",
        "programs.view_program", "programs.view_project", "programs.view_activity",
        "documents.view_document",
        "collaboration.view_task", "collaboration.change_task",
        "collaboration.view_meeting",
        "communications.view_announcement", "reports.view_report",
    ],

    Role.VIEWER: READ_ALL,

    Role.CONTENT: [
        "cms.view_page", "cms.add_page", "cms.change_page", "cms.delete_page",
        "cms.view_newsarticle", "cms.add_newsarticle", "cms.change_newsarticle",
        "cms.delete_newsarticle", "cms.publish_article", "cms.view_event", "cms.add_event",
        "cms.change_event", "cms.delete_event", "cms.view_mediaitem",
        "cms.add_mediaitem", "cms.change_mediaitem", "cms.delete_mediaitem", "cms.view_impactstat",
        "cms.add_impactstat", "cms.change_impactstat", "cms.delete_impactstat",
        "cms.view_teammember", "cms.add_teammember", "cms.change_teammember", "cms.delete_teammember",
        "cms.view_contactmessage", "cms.change_contactmessage",
        "partners.view_partner", "partners.add_partner", "partners.change_partner", "partners.delete_partner",
        "cms.view_carouselslide", "cms.add_carouselslide",
        "cms.change_carouselslide", "cms.delete_carouselslide",
        "documents.view_document", "documents.add_document",
        "hr.view_vacancy", "hr.change_vacancy",
        "communications.view_announcement",
    ],
}


def permissions_for_role(role):
    """Return the permission set for a role (supports the '*' wildcard)."""
    return set(ROLE_PERMISSIONS.get(role, []))


class GHDIPermissionBackend:
    """Resolves permissions from the static role matrix (no DB round-trips)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        return None  # authentication handled by ModelBackend

    def get_user(self, user_id):
        from django.contrib.auth import get_user_model

        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

    def _get_permissions(self, user_obj):
        if not user_obj.is_active or user_obj.is_anonymous:
            return set()
        if user_obj.is_superuser:
            return {"*"}
        return permissions_for_role(user_obj.role)

    def has_perm(self, user_obj, perm, obj=None):
        perms = self._get_permissions(user_obj)
        if "*" in perms:
            return True
        if perm in perms:
            return True
        app_label = perm.split(".")[0]
        return f"{app_label}.*" in perms

    def has_module_perms(self, user_obj, app_label):
        perms = self._get_permissions(user_obj)
        if "*" in perms:
            return True
        return any(p == app_label or p.startswith(f"{app_label}.") for p in perms)


DASHBOARD_BY_ROLE = {
    Role.ADMIN: "dashboard:admin",
    Role.EXEC: "dashboard:executive",
    Role.HR: "dashboard:hr",
    Role.PM: "dashboard:program",
    Role.FIN: "dashboard:finance",
    Role.MEAL: "dashboard:meal",
    Role.CONTENT: "dashboard:staff",
    Role.PROC: "dashboard:procurement",
    Role.STAFF: "dashboard:staff",
    Role.VIEWER: "dashboard:staff",
}

