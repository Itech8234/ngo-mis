"""Development settings - SQLite database, console email, verbose errors."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
# The shared settings may have read production flags from .env before this
# module switches DEBUG on. Keep local HTTP and Django's test client usable.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = list(dict.fromkeys([*(ALLOWED_HOSTS or ["*"]), "testserver"]))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Honour DATABASE_URL when provided even in development.
if env("DATABASE_URL"):
    DATABASES = {"default": parse_database_url(env("DATABASE_URL"))}
