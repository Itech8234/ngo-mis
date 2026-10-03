"""Non-public storage for personnel documents."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible
from pathlib import Path


@deconstructible
class PrivateHRStorage(FileSystemStorage):
    """Store HR files outside MEDIA_ROOT and refuse URL generation."""

    def __init__(self, *args, **kwargs):
        private_root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        if private_root == media_root or media_root in private_root.parents:
            raise ImproperlyConfigured("PRIVATE_MEDIA_ROOT must be outside MEDIA_ROOT so personnel files cannot be served as public media.")
        kwargs.setdefault("location", private_root)
        kwargs.setdefault("base_url", "/_private-hr-files/")
        super().__init__(*args, **kwargs)

    def url(self, name):
        raise ValueError("HR documents must be served through the permission-checked download view.")
