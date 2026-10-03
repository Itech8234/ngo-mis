"""Public GHDI website URLs (mounted at /)."""
from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("governance/", views.governance, name="governance"),
    path("programs/", views.public_programs, name="programs"),
    path("impact/", views.impact, name="impact"),
    path("partners/", views.partners_public, name="partners"),
    path("leadership/", views.leadership, name="leadership"),
    path("careers/", views.careers, name="careers"),
    path("news/", views.news_list, name="news_list"),
    path("news/<slug:slug>/", views.news_detail, name="news_detail"),
    path("stories/", views.stories, name="stories"),
    path("events/", views.events_list, name="events_list"),
    path("events/<slug:slug>/", views.event_detail, name="event_detail"),
    path("donate/", views.donate, name="donate"),
    path("contact/", views.contact, name="contact"),
    # Permanent institutional/legal addresses — served by dedicated views that
    # fall back to bundled copy, so they can never 404 before CMS seeding.
    path("privacy-policy/", views.privacy, name="privacy"),
    path("terms-of-use/", views.terms, name="terms"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("offline/", views.offline_page, name="offline"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("<slug:slug>/", views.page_detail, name="page_detail"),
]
