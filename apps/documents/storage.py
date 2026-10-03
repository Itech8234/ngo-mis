"""Storage for organisational documents that must never be public media."""
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateDocumentStorage(FileSystemStorage):
    """Keep files outside MEDIA_ROOT and serve only through authorized views."""

    def __init__(self, *args, **kwargs):
        private_root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        if private_root == media_root or media_root in private_root.parents:
            raise ImproperlyConfigured(
                "PRIVATE_MEDIA_ROOT must be outside MEDIA_ROOT so documents cannot be served publicly."
            )
        kwargs.setdefault("location", private_root)
        kwargs.setdefault("base_url", "/_private-documents/")
        super().__init__(*args, **kwargs)

    def url(self, name):
        raise ValueError("Organisational documents must use the permission-checked download view.")
