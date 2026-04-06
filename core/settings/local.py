"""
Local development settings.
Uses SQLite for simplicity — no PostgreSQL required.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['*']

# Override database to SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# More permissive CORS for local dev
CORS_ALLOW_ALL_ORIGINS = True
