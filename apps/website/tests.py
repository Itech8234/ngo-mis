from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.cms.models import Event, MediaItem, NewsArticle, Page


class PublicMediaWorkflowTests(TestCase):
    def test_all_public_landing_routes_render_without_seeded_content(self):
        paths = [
            "/", "/about/", "/governance/", "/programs/", "/impact/", "/partners/",
            "/leadership/", "/careers/", "/news/", "/stories/", "/events/",
            "/gallery/", "/videos/", "/contact/", "/donate/", "/privacy-policy/", "/terms-of-use/",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_published_cms_page_updates_fixed_route_presentation(self):
        Page.objects.create(
            title="Our updated programmes", slug="programs", summary="Programmes led by communities.",
            status="published", content="Editors can update this introduction.",
        )

        response = self.client.get("/programs/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Our updated programmes")
        self.assertContains(response, "Programmes led by communities.")
        self.assertContains(response, "Editors can update this introduction.")

    def test_public_gallery_filters_private_images(self):
        MediaItem.objects.create(
            title="Community learning session", media_type=MediaItem.MediaType.IMAGE,
            file="media_library/community.jpg", category="Education", is_public=True,
        )
        MediaItem.objects.create(
            title="Private staff document image", media_type=MediaItem.MediaType.IMAGE,
            file="media_library/private.jpg", is_public=False,
        )

        response = self.client.get("/gallery/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Community learning session")
        self.assertNotContains(response, "Private staff document image")

    def test_public_video_page_embeds_youtube_and_hides_private_video(self):
        MediaItem.objects.create(
            title="Community programme film", media_type=MediaItem.MediaType.VIDEO,
            video_url="https://youtu.be/abc123DEF", is_public=True,
        )
        MediaItem.objects.create(
            title="Internal training", media_type=MediaItem.MediaType.VIDEO,
            video_url="https://youtu.be/xyz123DEF", is_public=False,
        )

        response = self.client.get("/videos/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Community programme film")
        self.assertContains(response, "youtube-nocookie.com/embed/abc123DEF")
        self.assertNotContains(response, "Internal training")

    def test_cms_published_news_and_upcoming_event_render_publicly(self):
        NewsArticle.objects.create(
            title="Published community update", slug="published-community-update",
            category=NewsArticle.Category.NEWS, status="published", summary="A current update.",
        )
        Event.objects.create(
            name="Community partners meeting", slug="community-partners-meeting",
            date=timezone.localdate() + timedelta(days=5), status=Event.Status.UPCOMING,
        )

        news = self.client.get("/news/")
        events = self.client.get("/events/")
        homepage = self.client.get("/")

        self.assertEqual(news.status_code, 200)
        self.assertContains(news, "Published community update")
        self.assertEqual(events.status_code, 200)
        self.assertContains(events, "Community partners meeting")
        self.assertEqual(homepage.status_code, 200)
        self.assertContains(homepage, "Community partners meeting")
