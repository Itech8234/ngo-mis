"""Global template context for GHDI: organisation, navigation, notifications."""
from django.conf import settings
from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.core.models import OrganizationSetting
from apps.core.navigation import bottom_nav_for, quick_actions_for, sidebar_for


#: Public website navigation. (label, url name, match prefix, show in top bar)
PUBLIC_NAV = (
    ("Home", "website:home", "/", True),
    ("Impact", "website:impact", "/impact/", True),
    ("Partners", "website:partners", "/partners/", True),
    ("Contact", "website:contact", "/contact/", True),
)


def _public_nav(path):
    """Resolve the public nav to plain dicts with ``active``/``primary`` flags.

    Keeps templates free of per-link conditionals and guarantees a single
    source of truth for both the desktop bar and the mobile drawer. ``primary``
    marks the items that fit comfortably in the desktop top bar; the remainder
    are always available in the mobile drawer.
    """
    items = []
    for label, name, prefix, primary in PUBLIC_NAV:
        try:
            url = reverse(name)
        except NoReverseMatch:  # pragma: no cover - defensive
            continue
        if prefix == "/":
            active = path == "/"
        else:
            active = path.startswith(prefix)
        items.append({"label": label, "url": url, "active": active, "primary": primary})
    return items


def ghdi(request):
    user = getattr(request, "user", None)
    org = None
    try:
        org = OrganizationSetting.load()
    except Exception:  # database not yet migrated
        org = None

    context = {
        "ghdi_org": org,
        "ghdi_org_name": org.name if org else settings.GHDI_ORG_NAME,
        "ghdi_acronym": org.acronym if org else settings.GHDI_ORG_ACRONYM,
        "site_nav": _public_nav(getattr(request, "path", "/")),
    }
    try:
        from apps.cms.models import Page
        from apps.cms.models import FIXED_SITE_PAGE_SLUGS
        context["site_nav_pages"] = Page.objects.filter(
            status="published", show_in_nav=True,
        ).exclude(slug__in=FIXED_SITE_PAGE_SLUGS).filter(Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now())).order_by("nav_order", "title")
    except Exception:  # database can be absent before initial migrations
        context["site_nav_pages"] = []
    if user is not None and user.is_authenticated:
        context.update(
            {
                "sidebar_items": sidebar_for(user),
                "quick_actions": quick_actions_for(user),
                "bottom_nav": bottom_nav_for(user),
                "unread_notifications": user.notifications.filter(is_read=False).count()
                if hasattr(user, "notifications")
                else 0,
            }
        )
    else:
        context.update(
            {
                "sidebar_items": [],
                "quick_actions": [],
                "bottom_nav": [],
                "unread_notifications": 0,
            }
        )
    return context
