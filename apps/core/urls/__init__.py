"""Internal GHDI application URLs. All mounted under /app/.

Only the core-owned pages (global search and organisation/system settings)
live here. Module CRUD routes are mounted directly in ``config.urls`` so each
app keeps its own top-level URL namespace (e.g. ``programs:``, ``hr:``).
"""
from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("search/", views.search_view, name="search"),
    path("search/suggest/", views.search_suggest, name="search_suggest"),
    path("settings/", views.settings_index, name="settings"),
    path("settings/organization/", views.settings_org, name="settings_org"),
    path("settings/system/", views.settings_system, name="settings_system"),
]