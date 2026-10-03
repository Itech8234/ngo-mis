"""GHDI URL configuration.

Two logical areas:
- ``/``            the public GHDI website (CMS-driven)
- ``/app/``        the internal management information system

Authentication endpoints live at the root (``/login/``) for clean URLs.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import RedirectView

from apps.cms.sitemaps import SITEMAPS

admin.site.site_header = "GHDI Administration"
admin.site.site_title = "GHDI Admin"
admin.site.index_title = "GHDI Management Information System"

urlpatterns = [
    # --- Internal MIS module routes (mounted at /app/, each app keeps its own
    # top-level URL namespace). These MUST resolve before the public site's
    # catch-all `<slug:slug>/` page router, otherwise /app/, /login/ and
    # /admin/ would be swallowed by the website's dynamic page lookup.
    # /app/ redirects to the logged-in user's role dashboard.
    path("app/", RedirectView.as_view(pattern_name="dashboard:index"), name="app-root"),
    # Dashboard app mounted under /app/dashboard/ so its routes (executive, hr,
    # finance, procurement, ...) can never shadow module roots such as
    # /app/procurement/ (request list) or /app/finance/ (finance module home).
    path("app/dashboard/", include("apps.dashboard.urls")),
    path("app/hr/", include("apps.hr.urls")),
    path("app/programs/", include("apps.programs.urls")),
    path("app/beneficiaries/", include("apps.beneficiaries.urls")),
    path("app/monitoring/", include("apps.monitoring.urls")),
    path("app/finance/", include("apps.finance.urls")),
    path("app/partners/", include("apps.partners.urls")),
    path("app/procurement/", include("apps.procurement.urls")),
    path("app/assets/", include("apps.assets.urls")),
    path("app/documents/", include("apps.documents.urls")),
    path("app/collaboration/", include("apps.collaboration.urls")),
    path("app/communications/", include("apps.communications.urls")),
    path("app/notifications/", include("apps.notifications.urls")),
    path("app/risk/", include("apps.risk.urls")),
    path("app/reports/", include("apps.reports.urls")),
    path("app/audit/", include("apps.audit.urls")),
    path("app/cms/", include("apps.cms.urls")),
    path("app/", include("apps.core.urls")),
    # --- Public / auth routes
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("", include("apps.website.urls")),
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.svg", permanent=True)),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="django.contrib.sitemaps.views.sitemap"),
]

# Friendly branded error pages (production always uses these)
handler400 = "django.views.defaults.bad_request"
handler403 = "django.views.defaults.permission_denied"
handler404 = "apps.core.views.page_not_found"
handler500 = "django.views.defaults.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
