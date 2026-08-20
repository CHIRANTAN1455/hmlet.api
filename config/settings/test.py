"""Settings for the test suite.

Kept separate so tests never pick up developer-local .env values, and so the
slow-by-design bits of production config can be swapped for fast equivalents.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SECRET_KEY = "test-only-secret-key-not-used-anywhere-real"

# PBKDF2 deliberately burns CPU to slow down attackers. In tests it slows down
# only us, and every fixture creates a user.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# CI supplies DATABASE_URL; locally this falls back to the dev database, and
# pytest-django creates a separate test_* database from it either way.
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgres://pms:pms@localhost:5432/property_management",
    )
}

# Nothing under test asserts on log output; keep the run readable.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
