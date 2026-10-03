"""Global template context for GHDI: organisation, navigation, notifications."""
from django.conf import settings
from django.urls import NoReverseMatch, reverse

from apps.core.models import OrganizationSetting
from apps.core.navigation import bottom_nav_for, quick_actions_for, sidebar_for


#: Public website navigation. (label, url name, match prefix, show in top bar)
PUBLIC_NAV = (
    ("Home", "website:home", "/", True),
    ("About", "website:about", "/about/", True),
    ("What we do", "website:programs", "/programs/", True),
    ("Impact", "website:impact", "/impact/", True),
    ("News", "website:news_list", "/news/", True),
    ("Stories", "website:stories", "/stories/", False),
    ("Events", "website:events_list", "/events/", True),
    ("Partners", "website:partners", "/partners/", True),
    ("Donate", "website:donate", "/donate/", True),
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
