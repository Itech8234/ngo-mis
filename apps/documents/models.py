"""Central document management with versioning and access levels."""
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import OwnedModel
from apps.core.validators import FileSizeValidator, FileTypeValidator
from .storage import PrivateDocumentStorage


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "document categories"

    def __str__(self):
        return self.name


class AccessLevel(models.TextChoices):
    STAFF = "staff", "All Staff"
    RESTRICTED = "restricted", "Restricted"
    CONFIDENTIAL = "confidential", "Confidential"


class Document(OwnedModel):
    """Any organisational document, optionally linked to another object."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to="documents/%Y/%m/", storage=PrivateDocumentStorage(),
        validators=[FileSizeValidator(), FileTypeValidator()],
    )
    category = models.ForeignKey(DocumentCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="owned_documents")
    access_level = models.CharField(max_length=15, choices=AccessLevel.choices, default=AccessLevel.STAFF)
    tags = models.CharField(max_length=255, blank=True, help_text="Comma-separated tags")
    version = models.PositiveSmallIntegerField(default=1)
    expires_at = models.DateField(null=True, blank=True, db_index=True)
    # Optional link to any object (employee, project, donor, ...)
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    linked_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        ordering = ("-created_at",)
        permissions = [
            ("view_restricted_document", "Can view restricted organisational documents"),
            ("view_confidential_document", "Can view confidential organisational documents"),
        ]

    @property
    def expiring_soon(self):
        return bool(self.expires_at) and self.expires_at <= timezone.localdate() + timezone.timedelta(days=30)

    @property
    def is_expired(self):
        return bool(self.expires_at) and self.expires_at < timezone.localdate()

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def get_absolute_url(self):
        return reverse("documents:document_detail", args=[self.pk])

    @property
    def is_organizational_document(self):
        return True

    def __str__(self):
        return self.title


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    file = models.FileField(
        upload_to="documents/versions/%Y/%m/", storage=PrivateDocumentStorage(),
        validators=[FileSizeValidator(), FileTypeValidator()],
    )
    version = models.PositiveSmallIntegerField()
    note = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-version",)

    def __str__(self):
        return f"{self.document.title} v{self.version}"
