"""
Django settings for Project Management System.
Software Engineering Mini-Project 27.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

def parse_boolean_setting(value, *, name, default):
    """Parse a boolean environment setting or fail clearly on invalid input."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(
        f"{name} must be a boolean: true/false, yes/no, on/off, or 1/0"
    )


def parse_allowed_hosts(value):
    """Parse comma-separated hosts and reject an empty list."""
    hosts = [host.strip() for host in (value or "").split(",") if host.strip()]
    if not hosts:
        raise ImproperlyConfigured("ALLOWED_HOSTS must contain at least one host")
    return hosts


_LOCAL_DEVELOPMENT_SECRET = "django-insecure-local-development-only-do-not-deploy"
_SECRET_KEY_PLACEHOLDERS = {
    "replace-with-a-generated-secret-key",
    "change-this-in-production-random-secret-key-32-chars",
    "django-insecure-project-mgmt-sys-dev-key-change-in-prod-2026",
    _LOCAL_DEVELOPMENT_SECRET,
}


def resolve_secret_key(configured_key, *, debug):
    """Reject example keys and require an explicit strong production key."""
    configured_key = (configured_key or "").strip()
    if not configured_key:
        if debug:
            return _LOCAL_DEVELOPMENT_SECRET
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false"
        )

    if configured_key.casefold() in {
        key.casefold() for key in _SECRET_KEY_PLACEHOLDERS
    }:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY contains an example or development-only value; "
            "generate a unique key"
        )
    if not debug and len(configured_key) < 50:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be at least 50 characters when DJANGO_DEBUG is false"
        )
    return configured_key


def resolve_allowed_hosts(value, *, debug):
    """Require a safe, explicit host allowlist in production."""
    if value is None:
        if debug:
            return ["127.0.0.1", "localhost"]
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS must be explicitly set when DJANGO_DEBUG is false"
        )

    hosts = parse_allowed_hosts(value)
    if not debug and "*" in hosts:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS cannot contain '*' when DJANGO_DEBUG is false"
        )
    return hosts


DEBUG = parse_boolean_setting(
    os.getenv("DJANGO_DEBUG"), name="DJANGO_DEBUG", default=False
)
SECRET_KEY = resolve_secret_key(os.getenv("DJANGO_SECRET_KEY"), debug=DEBUG)
ALLOWED_HOSTS = resolve_allowed_hosts(os.getenv("ALLOWED_HOSTS"), debug=DEBUG)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Local Apps
    'accounts.apps.AccountsConfig',
    'projects.apps.ProjectsConfig',
    'tasks.apps.TasksConfig',
    'audit.apps.AuditConfig',
    'notifications.apps.NotificationsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'projects:project_list'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Security settings (SRS SR-02, SR-03)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 86400  # 1 day
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SESSION_COOKIE_SECURE = parse_boolean_setting(
    os.getenv("DJANGO_SECURE_COOKIES"),
    name="DJANGO_SECURE_COOKIES",
    default=not DEBUG,
)

CSRF_COOKIE_HTTPONLY = False  # Allows JS to read for fetch API header
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE


MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
