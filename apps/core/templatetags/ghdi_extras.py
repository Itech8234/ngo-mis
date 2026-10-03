"""General template helpers: badges, currency, dates, status colours."""
from django import template
from django.utils import timezone

register = template.Library()

BADGE_COLORS = {
    # workflow / generic
    "draft": "badge-gray", "submitted": "badge-blue", "under_review": "badge-amber",
    "approved": "badge-green", "rejected": "badge-red", "cancelled": "badge-gray",
    "completed": "badge-green",
    # programs
    "planned": "badge-blue", "active": "badge-green", "at_risk": "badge-red",
    "on_hold": "badge-amber", "closed": "badge-gray", "suspended": "badge-amber",
    "in_progress": "badge-blue", "delayed": "badge-red",
    # hr
    "on_leave": "badge-amber", "present": "badge-green", "absent": "badge-red",
    "late": "badge-amber", "remote": "badge-blue", "open": "badge-green",
    "filled": "badge-blue", "new": "badge-blue", "shortlisted": "badge-amber",
    "interview": "badge-amber", "offer": "badge-blue", "hired": "badge-green",
    "ongoing": "badge-blue",
    # procurement / finance
    "procurement": "badge-amber", "purchased": "badge-blue", "outstanding": "badge-amber",
    "partially_retired": "badge-amber", "retired": "badge-green", "income": "badge-green",
    "expense": "badge-amber", "revised": "badge-amber",
    # risk / incidents
    "mitigating": "badge-amber", "escalated": "badge-red",
    "investigating": "badge-amber", "resolved": "badge-green",
    "low": "badge-green", "medium": "badge-amber", "high": "badge-red",
    "critical": "badge-red", "urgent": "badge-red",
    # cms
    "review": "badge-amber", "scheduled": "badge-blue", "published": "badge-green",
    "archived": "badge-gray", "upcoming": "badge-blue",
    # tasks
    "todo": "badge-gray", "done": "badge-green", "blocked": "badge-red",
    # assets
    "in_use": "badge-green", "in_store": "badge-gray",
    "under_maintenance": "badge-amber", "disposed": "badge-gray", "lost": "badge-red",
    # locations/misc
    "prospect": "badge-blue", "ended": "badge-gray",
    "good": "badge-green", "fair": "badge-amber", "poor": "badge-red",
    "damaged": "badge-red", "new_asset": "badge-green",
}


@register.filter
def initials(value, limit=3):
    """Uppercase monogram for an organisation name.

    ``"Save the Children International"`` -> ``"SCI"``. Single-word names keep
    two letters so the logo tile is never a lone character.
    """
    import re

    if not value:
        return ""
    words = [w for w in re.split(r"[^\w&]+", str(value)) if w]
    if not words:
        return ""
    stop = {"the", "of", "and", "for", "a", "an", "de", "del", "da", "la", "le"}
    picked = [w for w in words if w.lower() not in stop] or words
    if len(picked) == 1:
        return picked[0][:2].upper()
    return "".join(w[0] for w in picked[: limit]).upper()


@register.filter
def media_url(field):
    """Return a file/ImageField URL, or '' when no file is attached.

    ``{{ obj.image.url }}`` raises ``ValueError`` on an empty ``FieldFile``,
    which breaks the entire page render (500) instead of simply hiding the
    image. Use this filter for optional imagery, e.g.
    ``{% include ... with hero_image=page.featured_image|media_url %}``.
    """
    return file_url(field)


@register.filter
def file_url(field):
    """URL for a FileField, but only when the file really exists in storage.

    ``{{ obj.logo.url }}`` returns a URL for any stored *name* — including one
    whose file was deleted or never uploaded — which renders a broken image and
    logs an HTTP 404 on every page load. Returning ``''`` instead lets the
    template fall back to its monogram/brand placeholder.
    """
    try:
        if not field:
            return ""
        name = getattr(field, "name", "")
        storage = getattr(field, "storage", None)
        if name and storage is not None and not storage.exists(name):
            return ""
        return field.url
    except (ValueError, OSError):
        return ""


@register.filter
def video_embed_url(url):
    """Convert a YouTube or Vimeo page URL into a privacy-friendly embed URL.

    Returns '' for anything else so templates never render a broken iframe.
    Accepts watch URLs, short links (youtu.be), /embed/ URLs and Vimeo links.
    """
    if not url:
        return ""
    import re
    from urllib.parse import parse_qs, urlparse

    text = str(url).strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if host in {"youtube.com", "m.youtube.com", "youtube-nocookie.com"}:
        video_id = (parse_qs(parsed.query).get("v") or [""])[0]
        if not video_id:
            match = re.match(r"/(?:embed|shorts|live)/([\w-]+)", parsed.path)
            video_id = match.group(1) if match else ""
        if re.fullmatch(r"[\w-]{6,}", video_id):
            return f"https://www.youtube-nocookie.com/embed/{video_id}"
    elif host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
        if re.fullmatch(r"[\w-]{6,}", video_id):
            return f"https://www.youtube-nocookie.com/embed/{video_id}"
    elif host in {"vimeo.com", "player.vimeo.com"}:
        match = re.search(r"/(?:video/)?(\d+)(?:/|$)", parsed.path)
        if match:
            return f"https://player.vimeo.com/video/{match.group(1)}"
    return ""


@register.filter
def badge(status_value):
    """Return a badge class for a status value."""
    return BADGE_COLORS.get(str(status_value).lower(), "badge-gray")


@register.filter
def cur(value):
    """Format a currency amount with the NGN symbol."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    if abs(amount) >= 1_000_000:
        return f"₦{amount / 1_000_000:,.2f}M"
    if abs(amount) >= 1_000:
        return f"₦{amount / 1_000:,.1f}K"
    return f"₦{amount:,.2f}"


@register.filter
def cur_full(value):
    try:
        return f"₦{float(value):,.2f}"
    except (TypeError, ValueError):
        return value


@register.filter
def num(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value


@register.filter
def div(value, arg):
    """Safe division filter: value / arg (returns 0 on failure)."""
    try:
        divisor = float(arg)
        if not divisor:
            return 0
        return float(value) / divisor
    except (TypeError, ValueError):
        return 0


@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return 0


@register.filter
def pct(value, digits=0):
    try:
        return f"{float(value):.{int(digits)}f}%"
    except (TypeError, ValueError):
        return value


@register.filter
def humanize_code(value):
    return str(value).replace("_", " ").title()


# Fields hidden from generic auto-tables to keep them clean
_SKIP_FIELDS = {
    "id", "pk", "created_at", "updated_at", "created_by_id", "updated_by_id",
    "submitted_at", "submitted_by_id", "approved_at", "approved_by_id",
    "rejected_at", "rejected_by_id", "review_note", "photo", "logo", "avatar",
    "document", "file", "attachment", "evidence", "image", "last_login",
}


@register.filter
def fieldnames(obj):
    """Return meaningful field names for generic list tables (max 5)."""
    names = []
    for field in obj._meta.fields:
        if field.name in _SKIP_FIELDS or field.auto_created:
            continue
        if field.primary_key or getattr(field, "auto_created", False):
            continue
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            continue
        if field.name.endswith("_file"):
            continue
        names.append(field.name)
        if len(names) >= 5:
            break
    return names


@register.filter
def fieldvalues(obj):
    """Return display values for the fields chosen by fieldnames."""
    values = []
    for name in fieldnames(obj):
        field = obj._meta.get_field(name)
        value = getattr(obj, name)
        if field.is_relation:
            try:
                value = str(value)
            except Exception:
                value = "—"
            values.append(value or "—")
        elif field.choices:
            values.append(dict(field.choices).get(value, value))
        elif isinstance(value, bool):
            values.append("Yes" if value else "No")
        elif getattr(field, "get_internal_type", lambda: "")() in ("DecimalField", "FloatField", "IntegerField"):
            values.append(f"{value:,}" if value is not None else "—")
        elif value is None:
            values.append("—")
        else:
            values.append(str(value))
    return values


@register.filter
def fieldpairs(obj):
    """Return [(label, value), ...] pairs for all meaningful fields."""
    pairs = []
    for name in fieldnames(obj):
        field = obj._meta.get_field(name)
        value = getattr(obj, name)
        if field.is_relation:
            display = str(value) if value else "—"
        elif field.choices:
            display = dict(field.choices).get(value, value) or "—"
        elif isinstance(value, bool):
            display = "Yes" if value else "No"
        elif getattr(field, "get_internal_type", lambda: "")() in ("DecimalField", "FloatField", "IntegerField"):
            display = f"{value:,}" if value is not None else "—"
        elif value is None:
            display = "—"
        else:
            display = str(value)
        pairs.append((humanize_code(name), display))
    return pairs


@register.filter
def days_until(date_value):
    if not date_value:
        return None
    return (date_value - timezone.localdate()).days


@register.simple_tag
def query_params(request, **kwargs):
    """Return a complete query string, preserving existing GET params.

    The result already includes the leading "?" (and is an empty string when no
    params remain), so templates use it directly::

        <a href="{% query_params request page=2 %}">

    Passing a param as ``None`` or ``""`` removes it from the string.
    """
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else ""
