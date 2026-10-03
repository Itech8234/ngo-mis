"""File upload security validators (MIME type, extension, size)."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

# Extension whitelist per purpose.
DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "csv", "ppt", "pptx", "txt", "rtf"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg"}
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

# Map of allowed magic-number signatures (first bytes) -> extensions.
SIGNATURES = {
    b"%PDF": {"pdf"},
    b"\xd0\xcf\x11\xe0": {"doc", "xls", "ppt"},  # legacy MS Office (OLE2)
    b"PK\x03\x04": {"docx", "xlsx", "pptx"},  # OOXML (zip container)
    b"\x89PNG": {"png"},
    b"\xff\xd8\xff": {"jpg", "jpeg"},
    b"GIF8": {"gif"},
    b"RIFF": {"webp"},
    b"ID3": {"mp3"},
}


@deconstructible
class FileSizeValidator:
    """Validates uploaded file size against GHDI_MAX_UPLOAD_SIZE."""

    def __init__(self, max_bytes=None):
        self.max_bytes = max_bytes or settings.GHDI_MAX_UPLOAD_SIZE

    def __call__(self, value):
        if value.size > self.max_bytes:
            raise ValidationError(
                f"File is too large. Maximum allowed size is {self.max_bytes // (1024 * 1024)} MB."
            )

    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and self.max_bytes == other.max_bytes


@deconstructible
class FileTypeValidator:
    """Validates file extension and MIME type against a whitelist."""

    def __init__(self, allowed_extensions=None):
        self.allowed_extensions = {e.lower() for e in (allowed_extensions or ALLOWED_EXTENSIONS)}

    def __call__(self, value):
        name = value.name or ""
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if extension not in self.allowed_extensions:
            raise ValidationError(
                "File type not allowed. Allowed types: " + ", ".join(sorted(self.allowed_extensions)) + "."
            )
        # Sniff content where we recognise a signature; unknown signatures
        # (e.g. plain text/csv) are accepted, but content must never contradict
        # a declared whitelist member.
        header = getattr(value, "file", None)
        if header is not None:
            try:
                header.seek(0)
                magic = header.read(8)
                header.seek(0)
            except Exception:  # pragma: no cover - non-seekable
                return
            for signature, extensions in SIGNATURES.items():
                if magic.startswith(signature) and not (extensions & self.allowed_extensions):
                    raise ValidationError("File content does not match the allowed file types.")

    def __eq__(self, other):
        return isinstance(other, FileTypeValidator) and self.allowed_extensions == other.allowed_extensions
