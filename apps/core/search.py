"""Global search across GHDI modules, respecting RBAC permissions."""
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

# (label, model, search fields, permission, url name for detail)
SEARCH_REGISTRY = [
    ("Employee", "hr", "Employee", ("first_name", "last_name", "employee_id", "position"), "hr.view_employee", "hr:employee_detail"),
    ("Program", "programs", "Program", ("title", "code", "description"), "programs.view_program", "programs:program_detail"),
    ("Project", "programs", "Project", ("name", "code", "objectives"), "programs.view_project", "programs:project_detail"),
    ("Activity", "programs", "Activity", ("name", "description"), "programs.view_activity", "programs:activity_detail"),
    ("Beneficiary", "beneficiaries", "Beneficiary", ("code", "full_name", "community"), "beneficiaries.view_beneficiary", "beneficiaries:beneficiary_detail"),
    ("Transaction", "finance", "Transaction", ("reference", "description"), "finance.view_transaction", "finance:transaction_detail"),
    ("Document", "documents", "Document", ("title", "description"), "documents.view_document", "documents:document_detail"),
    ("Donor", "partners", "Donor", ("name", "contact_name"), "partners.view_donor", "partners:donor_detail"),
    ("Partner", "partners", "Partner", ("name", "contact_person"), "partners.view_partner", "partners:partner_detail"),
    ("Task", "collaboration", "Task", ("title", "description"), "collaboration.view_task", "collaboration:task_detail"),
    ("Meeting", "collaboration", "Meeting", ("title", "agenda"), "collaboration.view_meeting", "collaboration:meeting_detail"),
    ("Indicator", "monitoring", "Indicator", ("name", "code"), "monitoring.view_indicator", "monitoring:indicator_detail"),
    ("Vendor", "procurement", "Vendor", ("name", "contact_person"), "procurement.view_vendor", "procurement:vendor_detail"),
]


def _model_for(app_label, model_name):
    try:
        return ContentType.objects.get(app_label=app_label, model=model_name.lower()).model_class()
    except ContentType.DoesNotExist:  # pragma: no cover
        return None


def global_search(query, user, limit_per_type=6):
    """Search all registered models. Returns [{label, results}] respecting perms."""
    if not query or len(query.strip()) < 2:
        return []
    term = query.strip()
    results = []
    for label, app_label, model_name, fields, perm, url_name in SEARCH_REGISTRY:
        if not user.has_perm(perm):
            continue
        model = _model_for(app_label, model_name)
        if model is None:
            continue
        q = Q()
        for field in fields:
            q |= Q(**{f"{field}__icontains": term})
        qs = model.objects.filter(q)[:limit_per_type]
        for obj in qs:
            detail_url = ""
            try:
                detail_url = obj.get_absolute_url()
            except AttributeError:
                try:
                    from django.urls import reverse

                    detail_url = reverse(url_name, args=[obj.pk])
                except Exception:  # pragma: no cover
                    detail_url = ""
            results.append(
                {
                    "label": label,
                    "title": str(obj),
                    "url": detail_url,
                }
            )
    return results
