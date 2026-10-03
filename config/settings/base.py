"""
GHDI NGO Management Information System - base settings.

Shared settings for all environments. Environment-specific settings
(dev.py, prod.py) import from here. All secrets and environment-specific
configuration are read from environment variables (optionally loaded from
a local `.env` file, which must never be committed).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Minimal .env loader (no external dependency required)
# ---------------------------------------------------------------------------
def load_dotenv(path):
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv(BASE_DIR / ".env")


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    return env(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_int(name, default):
    try:
        return int(env(name, str(default)))
    except (TypeError, ValueError):
        return default


def parse_database_url(url):
    """Parse a postgres:// or sqlite:// DATABASE_URL without extra dependencies."""
    if url.startswith("sqlite://"):
        name = url.replace("sqlite://", "") or str(BASE_DIR / "db.sqlite3")
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": name}
    from urllib.parse import parse_qs, unquote, urlparse

    parsed = urlparse(url)
    database = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
        "CONN_MAX_AGE": 60,
    }
    query_options = parse_qs(parsed.query)
    options = {
        name: values[-1]
        for name, values in query_options.items()
        if name in {"sslmode", "sslrootcert", "connect_timeout"} and values
    }
    # Supabase requires SSL for hosted database connections. Preserve an
    # explicit URL setting, and default hosted Supabase URLs to encrypted use.
    if "sslmode" not in options and (
        (parsed.hostname or "").endswith(".supabase.co")
        or (parsed.hostname or "").endswith(".supabase.com")
    ):
        options["sslmode"] = "require"
    if options:
        database["OPTIONS"] = options
    return database


# ---------------------------------------------------------------------------
# Core Django configuration
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-key-change-me-in-production")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    # GHDI applications
    "apps.core",
    "apps.accounts",
    "apps.audit",
    "apps.notifications",
    "apps.dashboard",
    "apps.hr",
    "apps.programs",
    "apps.beneficiaries",
    "apps.monitoring",
    "apps.finance",
    "apps.partners",
    "apps.procurement",
    "apps.assets",
    "apps.documents",
    "apps.collaboration",
    "apps.communications",
    "apps.risk",
    "apps.reports",
    "apps.cms",
    "apps.website",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.CurrentRequestMiddleware",
    "apps.audit.middleware.AuditRequestMiddleware",
    "apps.core.middleware.Branded404Middleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.ghdi",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "apps.accounts.permissions.GHDIPermissionBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:index"
LOGOUT_REDIRECT_URL = "accounts:login"

# Brute-force protection (cache-backed lockout enforced by the login view)
LOGIN_MAX_ATTEMPTS = env_int("LOGIN_MAX_ATTEMPTS", 5)
LOGIN_LOCKOUT_SECONDS = env_int("LOGIN_LOCKOUT_SECONDS", 900)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ghdi-cache",
    }
}

SESSION_COOKIE_AGE = env_int("SESSION_TIMEOUT_SECONDS", 60 * 60 * 8)
SESSION_COOKIE_HTTPONLY = True
SESSION_SAVE_EVERY_REQUEST = True

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "Africa/Lagos")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "_static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = Path(env("PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media")))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email (credentials always from environment - never hard-coded)
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "GHDI <info@ghdi.org.ng>")

# Upload security
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
GHDI_MAX_UPLOAD_SIZE = 10 * 1024 * 1024

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# GHDI organisation defaults (editable at runtime via core.OrganizationSetting)
GHDI_ORG_NAME = "Garkuwa Humanitarian and Development Initiative"
GHDI_ORG_ACRONYM = "GHDI"
GHDI_CURRENCY = env("GHDI_CURRENCY", "NGN")
GHDI_EXEC_APPROVAL_THRESHOLD = 500000  # NGN - above this the ED must approve
GHDI_AUDIT_EXEMPT = ("audit.auditlog", "sessions.session", "admin.logentry", "contenttypes.contenttype")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

