from django.urls import path

from . import views

app_name = "communications"

urlpatterns = [
    path("announcements/", views.AnnouncementListView.as_view(), name="announcement_list"),
    path("announcements/new/", views.AnnouncementCreateView.as_view(), name="announcement_create"),
    path("announcements/<int:pk>/", views.AnnouncementDetailView.as_view(), name="announcement_detail"),
    path("announcements/<int:pk>/publish/", views.announcement_publish, name="announcement_publish"),
    path("inbox/", views.inbox, name="inbox"),
    path("messages/<int:pk>/", views.message_read, name="message_detail"),
]
