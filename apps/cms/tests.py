from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import MediaItem


class CMSEditorWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        admin = User.objects.create_superuser(
            username="cms-admin", email="cms-admin@example.org", password="SafePass123!",
        )
        self.client.force_login(admin)

    def test_site_page_registry_and_dashboard_are_accessible(self):
        dashboard = self.client.get(reverse("cms:dashboard"))
        page_registry = self.client.get(reverse("cms:site_pages"))

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Content workspace")
        self.assertEqual(page_registry.status_code, 200)
        self.assertContains(page_registry, "Homepage")
        self.assertContains(page_registry, "Add page content")

    def test_editor_can_publish_video_to_public_videos_page(self):
        response = self.client.post(reverse("cms:media_create"), {
            "title": "GHDI field programme", "media_type": MediaItem.MediaType.VIDEO,
            "video_url": "https://youtu.be/abc123DEF", "category": "Field work",
            "tags": "community", "alt_text": "", "description": "Field programme overview",
            "is_public": "on", "is_featured": "on", "sort_order": "0",
        })

        self.assertEqual(response.status_code, 302)
        item = MediaItem.objects.get(title="GHDI field programme")
        self.assertTrue(item.is_public)
        self.assertContains(self.client.get(reverse("website:videos")), "GHDI field programme")
