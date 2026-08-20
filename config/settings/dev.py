"""Local development settings. This is the default (see manage.py)."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = ["*"]

# Surface errors loudly while developing rather than swallowing them.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": env("DJANGO_SQL_LOG_LEVEL", default="WARNING"),
            "propagate": False,
        },
    },
}
