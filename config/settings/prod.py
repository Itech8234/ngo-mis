"""Production settings - PostgreSQL, hardened security, no debug."""
from .base import *  # noqa: F401,F403
from .base import env, parse_database_url
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

if SECRET_KEY == "dev-only-insecure-key-change-me":
    raise ImproperlyConfigured("Set a unique SECRET_KEY environment variable before starting GHDI in production.")

if env("DATABASE_URL"):
    DATABASES = {"default": parse_database_url(env("DATABASE_URL"))}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "ghdi"),
            "USER": env("DB_USER", "ghdi"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
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
