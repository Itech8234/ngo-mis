"""CMS models for the public GHDI website."""
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import OwnedModel
from apps.core.validators import ALLOWED_EXTENSIONS, FileSizeValidator, FileTypeValidator, IMAGE_EXTENSIONS


class PageStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    REVIEW = "review", "Review"
    SCHEDULED = "scheduled", "Scheduled"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


FIXED_SITE_PAGE_ROUTES = {
    "home": "website:home", "about-us": "website:about", "governance": "website:governance",
    "programs": "website:programs", "impact": "website:impact", "partners": "website:partners",
    "leadership": "website:leadership", "careers": "website:careers", "news": "website:news_list",
    "stories": "website:stories", "events": "website:events_list", "gallery": "website:gallery",
    "videos": "website:videos", "contact": "website:contact", "donate": "website:donate",
    "privacy-policy": "website:privacy", "terms-of-use": "website:terms",
}
FIXED_SITE_PAGE_SLUGS = set(FIXED_SITE_PAGE_ROUTES)


class Page(OwnedModel):
    """CMS page. Public visibility requires status=published (and schedule)."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    page_type = models.CharField(
        max_length=20,
        choices=[
            ("standard", "Standard"),
            ("thematic", "Thematic Area"),
            ("legal", "Legal / Policy"),
            ("governance", "Governance"),
        ],
        default="standard",
        db_index=True,
    )
    featured_image = models.ImageField(upload_to="cms/pages/", blank=True, validators=[FileSizeValidator()])
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True, help_text="Main page content. Use blank lines to separate paragraphs.")
    status = models.CharField(max_length=12, choices=PageStatus.choices, default=PageStatus.DRAFT, db_index=True)
    publish_at = models.DateTimeField(null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="cms_pages")
    is_featured = models.BooleanField(default=False)
    show_in_nav = models.BooleanField(default=False, help_text="Show in the public site navigation")
    nav_order = models.PositiveSmallIntegerField(default=0)
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    seo_keywords = models.CharField(max_length=300, blank=True)
    views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("nav_order", "title")

    def save(self, *args, **kwargs):
        # These slugs are fixed route content; their links are already placed in
        # the public navigation, so editors cannot accidentally duplicate them.
        if self.slug in FIXED_SITE_PAGE_SLUGS:
            self.show_in_nav = False
        super().save(*args, **kwargs)

    @property
    def is_live(self):
        if self.status != PageStatus.PUBLISHED:
            return False
        if self.publish_at and self.publish_at > timezone.now():
            return False
        return True

    @property
    def is_cms_page(self):
        return True

    def get_absolute_url(self):
        fixed_route = FIXED_SITE_PAGE_ROUTES.get(self.slug)
        if fixed_route:
            return reverse(fixed_route)
        return reverse("website:page_detail", args=[self.slug])

    def __str__(self):
        return self.title


class PageSection(models.Model):
    """Structured content block: avoids storing raw HTML from editors."""

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="sections")
    heading = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True, help_text="Plain text; blank lines create paragraphs.")
    image = models.ImageField(upload_to="cms/sections/", blank=True, validators=[FileSizeValidator()])
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"{self.page.title} - {self.heading or self.pk}"


class NewsArticle(OwnedModel):
    """News, impact stories, field updates and testimonials."""

    class Category(models.TextChoices):
        NEWS = "news", "News"
        STORY = "story", "Impact Story"
        FIELD = "field", "Field Update"
        TESTIMONIAL = "testimonial", "Testimonial"
        PRESS = "press", "Press Release"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    category = models.CharField(max_length=15, choices=Category.choices, default=Category.NEWS, db_index=True)
    featured_image = models.ImageField(upload_to="cms/news/", blank=True, validators=[FileSizeValidator()])
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True, help_text="Plain text; blank lines create paragraphs.")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    publish_at = models.DateTimeField(null=True, blank=True)
    tags = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=PageStatus.choices, default=PageStatus.DRAFT, db_index=True)
    is_featured = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    video_url = models.URLField(
        blank=True,
        help_text="Optional YouTube/Vimeo URL. When set, the article shows a featured video instead of the image.",
    )
    video_caption = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ("-publish_at", "-created_at")
        permissions = [("publish_article", "Can publish news and stories")]

    @property
    def is_live(self):
        if self.status != PageStatus.PUBLISHED:
            return False
        if self.publish_at and self.publish_at > timezone.now():
            return False
        return True

    @property
    def is_cms_article(self):
        return True

    def get_absolute_url(self):
        return reverse("website:news_detail", args=[self.slug])

    def __str__(self):
        return self.title


class Event(models.Model):
    """Public event for the website events page."""

    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    date = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, default="Damaturu")
    registration_link = models.URLField(blank=True)
    image = models.ImageField(upload_to="cms/events/", blank=True, validators=[FileSizeValidator()])
    organizer = models.CharField(max_length=160, blank=True, default="GHDI")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UPCOMING)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-date",)

    def get_absolute_url(self):
        return reverse("website:event_detail", args=[self.slug])

    @property
    def is_cms_event(self):
        return True

    def __str__(self):
        return self.name


class MediaItem(models.Model):
    """Media library entry (images, documents, videos, logos, reports)."""

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        DOCUMENT = "document", "Document"
        VIDEO = "video", "Video"
        LOGO = "logo", "Logo"
        REPORT = "report", "Report"

    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="media_library/", blank=True, validators=[FileSizeValidator(), FileTypeValidator(ALLOWED_EXTENSIONS | {"mp4", "webm", "ogv"})])
    video_url = models.URLField(blank=True, help_text="YouTube or Vimeo URL for a video item.")
    thumbnail = models.ImageField(upload_to="cms/media-thumbnails/", blank=True, validators=[FileSizeValidator()])
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.IMAGE, db_index=True)
    category = models.CharField(max_length=100, blank=True)
    tags = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "-created_at")

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.media_type == self.MediaType.VIDEO and not (self.video_url or self.file):
            raise ValidationError({"video_url": "Add a YouTube/Vimeo URL or upload a video file."})
        if self.media_type == self.MediaType.VIDEO and self.video_url:
            from apps.core.templatetags.ghdi_extras import video_embed_url
            if not video_embed_url(self.video_url):
                raise ValidationError({"video_url": "Use a valid YouTube or Vimeo video URL."})
        if self.media_type == self.MediaType.IMAGE and not self.file:
            raise ValidationError({"file": "Upload an image for a gallery item."})
        if self.media_type == self.MediaType.IMAGE and self.file:
            extension = self.file.name.rsplit(".", 1)[-1].lower() if "." in self.file.name else ""
            if extension not in IMAGE_EXTENSIONS - {"svg"}:
                raise ValidationError({"file": "Gallery images must be JPG, PNG, GIF or WebP files."})

    @property
    def public_image(self):
        return self.thumbnail if self.thumbnail else self.file

    def get_absolute_url(self):
        return reverse("cms:media_detail", args=[self.pk])

    def __str__(self):
        return self.title


class ImpactStat(models.Model):
    """Editable impact metrics shown on the public website."""

    label = models.CharField(max_length=100)
    value = models.PositiveIntegerField(default=0)
    suffix = models.CharField(max_length=10, blank=True, default="+")
    icon = models.CharField(max_length=30, blank=True, default="users")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order",)

    @property
    def display_value(self):
        return f"{self.value:,}{self.suffix}"

    @property
    def is_cms_impact(self):
        return True

    def __str__(self):
        return f"{self.label}: {self.display_value}"


class CarouselSlide(models.Model):
    """CMS-managed homepage hero slide."""

    eyebrow = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=160)
    title_highlight = models.CharField(max_length=160, blank=True)
    subtitle = models.TextField(blank=True)
    image = models.ImageField(upload_to="cms/carousel/", validators=[FileSizeValidator()])
    image_alt = models.CharField(max_length=200, blank=True)
    cta_label = models.CharField(max_length=60, blank=True)
    cta_url = models.CharField(max_length=500, blank=True, help_text="Internal path (for example /programs/) or HTTPS URL.")
    secondary_label = models.CharField(max_length=60, blank=True)
    secondary_url = models.CharField(max_length=500, blank=True, help_text="Internal path (for example /impact/) or HTTPS URL.")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order", "pk")

    @property
    def image_url(self):
        try:
            return self.image.url if self.image and self.image.storage.exists(self.image.name) else ""
        except (ValueError, OSError):
            return ""

    @property
    def is_carousel_slide(self):
        return True

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("cms:carousel_edit", args=[self.pk])


class TeamMember(models.Model):
    """Leadership and board members for the public site."""

    class Category(models.TextChoices):
        LEADERSHIP = "leadership", "Leadership"
        BOARD = "board", "Board of Trustees"
        MANAGEMENT = "management", "Management Team"

    name = models.CharField(max_length=160)
    role = models.CharField(max_length=160)
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.LEADERSHIP, db_index=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="cms/team/", blank=True, validators=[FileSizeValidator()])
    email = models.EmailField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("order", "name")

    @property
    def is_cms_team_member(self):
        return True

    def __str__(self):
        return f"{self.name} ({self.role})"


class DonationIntent(models.Model):
    """A pledge/interest recorded through the public donation page."""

    class Kind(models.TextChoices):
        ONE_OFF = "one_off", "One-off gift"
        MONTHLY = "monthly", "Monthly giving"
        IN_KIND = "in_kind", "In-kind donation"
        CORPORATE = "corporate", "Corporate partnership"

    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    kind = models.CharField(max_length=15, choices=Kind.choices, default=Kind.ONE_OFF)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="NGN")
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name}: {self.get_kind_display()}"


class ContactMessage(models.Model):
    """Message submitted through the public contact form."""

    name = models.CharField(max_length=160)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_handled = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name}: {self.subject}"

