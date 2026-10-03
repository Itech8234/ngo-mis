"""Sidebar navigation and quick-action registries, filtered by permissions.

Each item declares the Django permission required to be visible. Views must
still enforce permissions server-side — this only curates the UI.
"""
from django.urls import reverse

from apps.accounts.models import Role

# Sidebar: (label, url name, icon name, permission or None)
SIDEBAR_ITEMS = [
    ("Dashboard", "dashboard:index", "home", None),
    ("Programs", "programs:program_list", "layers", "programs.view_program"),
    ("Projects", "programs:project_list", "briefcase", "programs.view_project"),
    ("Activities", "programs:activity_list", "activity", "programs.view_activity"),
    ("Beneficiaries", "beneficiaries:beneficiary_list", "users", "beneficiaries.view_beneficiary"),
    ("MEAL", "monitoring:indicator_list", "target", "monitoring.view_indicator"),
    ("Finance", "finance:dashboard", "wallet", "finance.view_transaction"),
    ("Budgets", "finance:budget_list", "pie", "finance.view_budget"),
    ("Donors", "partners:donor_list", "handshake", "partners.view_donor"),
    ("Partners", "partners:partner_list", "network", "partners.view_partner"),
    ("Staff", "hr:employee_list", "idcard", "hr.view_employee"),
    ("Leave", "hr:leave_list", "calendar", "hr.view_leaverequest"),
    ("Leave balances", "hr:leave_balances", "calendar", "hr.view_leavebalance"),
    ("Attendance", "hr:attendance_list", "clock", "hr.view_attendancerecord"),
    ("Personnel documents", "hr:document_list", "file", "hr.view_hrdocument"),
    ("Recruitment", "hr:vacancy_list", "userplus", "hr.view_vacancy"),
    ("Training", "hr:training_list", "book", "hr.view_training"),
    ("Performance", "hr:performance_list", "chart", "hr.view_performancereview"),
    ("Staff relations", "hr:disciplinary_list", "shield", "hr.view_disciplinaryrecord"),
    ("Procurement", "procurement:request_list", "cart", "procurement.view_procurementrequest"),
    ("Vendors", "procurement:vendor_list", "store", "procurement.view_vendor"),
    ("Assets", "assets:asset_list", "box", "assets.view_asset"),
    ("Documents", "documents:document_list", "file", "documents.view_document"),
    ("Tasks", "collaboration:task_list", "check", "collaboration.view_task"),
    ("Meetings", "collaboration:meeting_list", "video", "collaboration.view_meeting"),
    ("Announcements", "communications:announcement_list", "megaphone", "communications.view_announcement"),
    ("Inbox", "communications:inbox", "mail", None),
    ("Risks", "risk:risk_list", "alert", "risk.view_risk"),
    ("Incidents", "risk:incident_list", "shield", "risk.view_incident"),
    ("Reports", "reports:hub", "chart", None),
    ("Activity Feed", "audit:feed", "rss", None),
    ("Audit Logs", "audit:log_list", "list", "audit.view_auditlog"),
    ("CMS", "cms:dashboard", "edit", "cms.view_page"),
    ("Settings", "core:settings_org", "settings", "core.change_organizationsetting"),
]

# Bottom navigation (mobile): role -> ordered (label, url name, icon) candidates.
# Only the first MAX_BOTTOM_ITEMS *permitted* entries are rendered, and "Home"
# is always injected first, so a role can never see a tab it cannot open.
BOTTOM_NAV_BY_ROLE = {
    Role.ADMIN: [
        ("Users", "accounts:user_list", "users"),
        ("Programs", "programs:program_list", "layers"),
        ("Reports", "reports:hub", "chart"),
        ("Audit", "audit:log_list", "list"),
        ("Settings", "core:settings_org", "settings"),
    ],
    Role.EXEC: [
        ("Programs", "programs:program_list", "layers"),
        ("Finance", "finance:dashboard", "wallet"),
        ("Reports", "reports:hub", "chart"),
        ("Activity", "audit:feed", "rss"),
    ],
    Role.HR: [
        ("Staff", "hr:employee_list", "idcard"),
        ("Leave", "hr:leave_list", "calendar"),
        ("Attendance", "hr:attendance_list", "clock"),
        ("Leave balances", "hr:leave_balances", "calendar"),
    ],
    Role.PM: [
        ("Programs", "programs:program_list", "layers"),
        ("Projects", "programs:project_list", "briefcase"),
        ("Activities", "programs:activity_list", "activity"),
        ("Beneficiaries", "beneficiaries:beneficiary_list", "users"),
    ],
    Role.FIN: [
        ("Finance", "finance:dashboard", "wallet"),
        ("Budgets", "finance:budget_list", "pie"),
        ("Payments", "finance:expense_list", "file"),
        ("Transactions", "finance:transaction_list", "chart"),
    ],
    Role.MEAL: [
        ("MEAL", "monitoring:indicator_list", "target"),
        ("Beneficiaries", "beneficiaries:beneficiary_list", "users"),
        ("Projects", "programs:project_list", "briefcase"),
        ("Reports", "reports:hub", "chart"),
    ],
    Role.PROC: [
        ("Procurement", "procurement:request_list", "cart"),
        ("Vendors", "procurement:vendor_list", "store"),
        ("Orders", "procurement:po_list", "box"),
        ("Reports", "reports:hub", "chart"),
    ],
    Role.CONTENT: [
        ("Content", "cms:dashboard", "edit"),
        ("News", "cms:news_list", "megaphone"),
        ("Events", "cms:event_list", "calendar"),
        ("Media", "cms:media_list", "file"),
    ],
    Role.STAFF: [
        ("Programs", "programs:program_list", "layers"),
        ("Tasks", "collaboration:task_list", "check"),
        ("Leave", "hr:leave_list", "calendar"),
        ("Activity", "audit:feed", "rss"),
    ],
    Role.VIEWER: [
        ("Programs", "programs:program_list", "layers"),
        ("Documents", "documents:document_list", "file"),
        ("Reports", "reports:hub", "chart"),
        ("Activity", "audit:feed", "rss"),
    ],
}

MAX_BOTTOM_ITEMS = 4  # plus the always-present Home tab

# Permission required to open each bottom-nav destination. Keeps the mobile tab
# bar honest: if a role's matrix stops granting access, the tab disappears
# instead of leading to a 403 page.
TAB_PERMISSIONS = {
    "accounts:user_list": "accounts.view_user",
    "programs:program_list": "programs.view_program",
    "programs:project_list": "programs.view_project",
    "programs:activity_list": "programs.view_activity",
    "beneficiaries:beneficiary_list": "beneficiaries.view_beneficiary",
    "monitoring:indicator_list": "monitoring.view_indicator",
    "finance:dashboard": "finance.view_transaction",
    "finance:budget_list": "finance.view_budget",
    "finance:expense_list": "finance.view_expenserequest",
    "finance:transaction_list": "finance.view_transaction",
    "hr:employee_list": "hr.view_employee",
    "hr:leave_list": "hr.view_leaverequest",
    "hr:leave_balances": "hr.view_leavebalance",
    "hr:attendance_list": "hr.view_attendancerecord",
    "hr:vacancy_list": "hr.view_vacancy",
    "hr:directory": "hr.view_employee",
    "procurement:request_list": "procurement.view_procurementrequest",
    "procurement:vendor_list": "procurement.view_vendor",
    "procurement:po_list": "procurement.view_purchaseorder",
    "collaboration:task_list": "collaboration.view_task",
    "documents:document_list": "documents.view_document",
    "cms:dashboard": "cms.view_page",
    "cms:news_list": "cms.view_newsarticle",
    "cms:event_list": "cms.view_event",
    "cms:media_list": "cms.view_mediaitem",
    "reports:hub": None,
    "audit:feed": None,
    "audit:log_list": "audit.view_auditlog",
    "core:settings_org": "core.change_organizationsetting",
}

# Quick actions: (label, url name, permission or None)
QUICK_ACTIONS = [
    ("New Program", "programs:program_create", "programs.add_program"),
    ("New Project", "programs:project_create", "programs.add_project"),
    ("New Activity", "programs:activity_create", "programs.add_activity"),
    ("Add Staff Member", "hr:employee_create", "hr.add_employee"),
    ("Request Leave", "hr:leave_create", "hr.add_leaverequest"),
    ("New Transaction", "finance:transaction_create", "finance.add_transaction"),
    ("New Budget", "finance:budget_create", "finance.add_budget"),
    ("Request Payment", "finance:expense_create", "finance.add_expenserequest"),
    ("Procurement Request", "procurement:request_create", "procurement.add_procurementrequest"),
    ("Upload Document", "documents:document_create", "documents.add_document"),
    ("Create Task", "collaboration:task_create", "collaboration.add_task"),
    ("Schedule Meeting", "collaboration:meeting_create", "collaboration.add_meeting"),
    ("Add Beneficiary", "beneficiaries:beneficiary_create", "beneficiaries.add_beneficiary"),
    ("Log Indicator", "monitoring:indicator_update_create", "monitoring.add_indicatorupdate"),
    ("Write News", "cms:news_create", "cms.add_newsarticle"),
    ("Create Event", "cms:event_create", "cms.add_event"),
    ("New Announcement", "communications:announcement_create", "communications.add_announcement"),
    ("Register Incident", "risk:incident_create", "risk.add_incident"),
]


def _has(user, perm):
    if perm is None:
        return True
    return user.has_perm(perm)


def sidebar_for(user):
    """Return sidebar items visible to the given user."""
    return [
        {"label": label, "url": reverse(url), "icon": icon}
        for label, url, icon, perm in SIDEBAR_ITEMS
        if _has(user, perm)
    ]


def quick_actions_for(user):
    """Return quick-action entries allowed for the given user."""
    return [
        {"label": label, "url": reverse(url)}
        for label, url, perm in QUICK_ACTIONS
        if _has(user, perm)
    ]


def bottom_nav_for(user):
    """Return mobile bottom-nav tabs for the user's role (permission-filtered).

    Home is always first; the remainder come from the role's own candidate list
    capped at ``MAX_BOTTOM_ITEMS`` permitted entries.
    """
    home = {"label": "Home", "url": reverse("dashboard:index"), "icon": "home"}
    items = [home]
    candidates = BOTTOM_NAV_BY_ROLE.get(getattr(user, "role", None), [])
    for label, url, icon in candidates:
        if len(items) > MAX_BOTTOM_ITEMS:
            break
        if not _has(user, TAB_PERMISSIONS.get(url)):
            continue
        items.append({"label": label, "url": reverse(url), "icon": icon})
    return items
