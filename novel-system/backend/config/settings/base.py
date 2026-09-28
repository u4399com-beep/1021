"""Base settings shared across environments."""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# ------------------------------------------------------------------
# Security
# ------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me-in-prod-please")
DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()]
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ------------------------------------------------------------------
# Apps
# ------------------------------------------------------------------
INSTALLED_APPS = [
    "rest_framework",
    "drf_spectacular",
    "django_celery_results",
    "django_celery_beat",
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # local
    "apps.account",
    "apps.novel",
    "apps.crawler",
    "apps.crawler_rules",
    "apps.crawler_tasks",
    "apps.content_cleaner",
    "apps.smart_classifier",
    "apps.themes",
    "apps.sites",
    "apps.file_download",
    "apps.seo",
    "apps.obfuscator",
    "apps.search",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.obfuscator.middleware.ObfuscatorMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "novel"),
        "USER": os.environ.get("DB_USER", "novel"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "novel"),
        "HOST": os.environ.get("DB_HOST", "postgres"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"options": "-c timezone=Asia/Shanghai"},
    },
}

# Optional read replica (v25) — set DATABASE_REPLICA_ENABLED=true to enable
DATABASE_REPLICA_ENABLED = os.environ.get("DATABASE_REPLICA_ENABLED", "false").lower() in ("true", "1", "yes")
if DATABASE_REPLICA_ENABLED:
    DATABASES["replica"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_REPLICA_NAME", DATABASES["default"]["NAME"]),
        "USER": os.environ.get("DB_REPLICA_USER", DATABASES["default"]["USER"]),
        "PASSWORD": os.environ.get("DB_REPLICA_PASSWORD", DATABASES["default"]["PASSWORD"]),
        "HOST": os.environ.get("DB_REPLICA_HOST", "postgres-replica"),
        "PORT": os.environ.get("DB_REPLICA_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"options": "-c timezone=Asia/Shanghai -c default_transaction_read_only=on"},
    }

DATABASE_ROUTERS = ["apps.read_replica.ReadReplicaRouter"] if DATABASE_REPLICA_ENABLED else []

# ------------------------------------------------------------------
# Auth / password
# ------------------------------------------------------------------
AUTH_USER_MODEL = "account.User"
PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------
# I18N / time
# ------------------------------------------------------------------
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# Static / media
# ------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------
# DRF
# ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Novel System API",
    "DESCRIPTION": "Django + Vue novel management system with multi-site crawler engine",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ------------------------------------------------------------------
# Redis / Celery
# ------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = "django-db"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 60 * 4       # 4h hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 60 * 3  # 3h soft limit
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ROUTES = {
    "apps.crawler_tasks.tasks.*": {"queue": "crawler"},
    "apps.crawler.tasks.*": {"queue": "crawler"},
    "apps.file_download.tasks.*": {"queue": "download"},
}
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ------------------------------------------------------------------
# Crawler engine configuration
# ------------------------------------------------------------------
CRAWLER = {
    # Firecrawl (1st tier) — pass empty string to disable
    "FIRECRAWL_API_KEY": os.environ.get("FIRECRAWL_API_KEY", ""),
    "FIRECRAWL_API_URL": os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1"),
    # Browser Use (2nd tier)
    "BROWSER_USE_OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    # Playwright (3rd tier) — always available as fallback
    "PLAYWRIGHT_HEADLESS": os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() == "true",
    "PLAYWRIGHT_PROXY": os.environ.get("PLAYWRIGHT_PROXY", ""),
    "PLAYWRIGHT_TIMEOUT": int(os.environ.get("PLAYWRIGHT_TIMEOUT", "30000")),
    # Hyperbrowser integration
    "HYPERBROWSER_API_KEY": os.environ.get("HYPERBROWSER_API_KEY", ""),
    # Default thread / interval
    "DEFAULT_THREADS_MIN": 2,
    "DEFAULT_THREADS_MAX": 5,
    "DEFAULT_INTERVAL_MIN": 1.0,
    "DEFAULT_INTERVAL_MAX": 3.0,
    # User-agent pool / cookie pool are DB-driven (see anti_detection pool)
    "REQ_TIMEOUT": (10, 30),
    "REQ_RETRY": 3,
    # Cover image
    "COVER_FORMAT": "webp",
    "COVER_QUALITY": 85,
    "COVER_DIR": str(BASE_DIR / "media" / "uploads" / "covers"),
    "CHAPTER_DIR": str(BASE_DIR / "media" / "chapters"),
    "DOWNLOAD_DIR": str(BASE_DIR / "media" / "downloads"),
    # Search-engine suggestion providers (configurable per site)
    "SUGGEST_PROVIDERS": ["baidu", "bing", "google", "sogou"],
    # Concurrency control — global max concurrent crawler tasks
    "MAX_CONCURRENT_TASKS": 8,
    # Captcha recognition service (configured in .env)
    "CAPTCHA_2CAPTCHA_KEY": os.environ.get("CAPTCHA_2CAPTCHA_KEY", ""),
    "CAPTCHA_2CAPTCHA_ENDPOINT": os.environ.get("CAPTCHA_2CAPTCHA_ENDPOINT", "https://2captcha.com/in.php"),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "app.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
    "loggers": {
        "celery": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
        "crawler_engine": {"handlers": ["console", "file"], "level": "INFO", "propagate": False},
    },
}
