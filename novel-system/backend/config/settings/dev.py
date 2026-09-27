"""Development settings — debug on, devtools enabled."""
from .base import *  # noqa
from .base import BASE_DIR  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += [  # type: ignore
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # type: ignore

INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]

# Show pretty DRF browseable API in dev
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # type: ignore[index]
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)
