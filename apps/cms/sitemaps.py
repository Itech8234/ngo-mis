"""SEO sitemaps for the public GHDI website."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "website:home", "website:about", "website:programs",
            "website:impact", "website:news_list", "website:stories",
            "website:events_list", "website:partners", "website:leadership",
            "website:careers", "website:contact", "website:governance",
            "website:gallery", "website:videos", "website:donate",
            "website:privacy", "website:terms",
        ]

    def location(self, item):
        return reverse(item)


class PageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        from .models import FIXED_SITE_PAGE_SLUGS, Page

        from django.db.models import Q
        from django.utils import timezone

        return Page.objects.filter(status="published").exclude(slug__in=FIXED_SITE_PAGE_SLUGS).filter(Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now()))

    def lastmod(self, obj):
        return obj.updated_at


class NewsSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.6

    def items(self):
        from .models import NewsArticle

        from django.db.models import Q
        from django.utils import timezone

        return NewsArticle.objects.filter(status="published").filter(Q(publish_at__isnull=True) | Q(publish_at__lte=timezone.now()))

    def lastmod(self, obj):
        return obj.publish_at or obj.updated_at


class EventSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        from .models import Event

        return Event.objects.filter(status__in=["upcoming", "ongoing"])

    def lastmod(self, obj):
        return obj.created_at


SITEMAPS = {
    "static": StaticSitemap,
    "pages": PageSitemap,
    "news": NewsSitemap,
    "events": EventSitemap,
}
