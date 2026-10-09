"""Development settings - SQLite database, console email, verbose errors."""
from .base import *  # noqa: F401,F403

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
