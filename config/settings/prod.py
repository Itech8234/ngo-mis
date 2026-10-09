"""Production settings - SQLite, hardened security, no debug."""
from .base import *  # noqa: F401,F403
from .base import env
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

if SECRET_KEY == "dev-only-insecure-key-change-me":
    raise ImproperlyConfigured("Set a unique SECRET_KEY environment variable before starting GHDI in production.")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# WhiteNoise for static asset serving when USE_WHITENOISE is enabled.
if env_bool("USE_WHITENOISE", True):
    INSTALLED_APPS = list(INSTALLED_APPS) + ["whitenoise.runserver_nostatic"]
    MIDDLEWARE = list(MIDDLEWARE)
    MIDDLEWARE[1] = "whitenoise.middleware.WhiteNoiseMiddleware"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
