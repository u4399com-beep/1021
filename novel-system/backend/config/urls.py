"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.account.urls")),
    path("api/v1/novels/", include("apps.novel.urls")),
    path("api/v1/crawler/", include("apps.crawler.urls")),
    path("api/v1/rules/", include("apps.crawler_rules.urls")),
    path("api/v1/tasks/", include("apps.crawler_tasks.urls")),
    path("api/v1/cleaner/", include("apps.content_cleaner.urls")),
    path("api/v1/classifier/", include("apps.smart_classifier.urls")),
    path("api/v1/themes/", include("apps.themes.urls")),
    path("api/v1/sites/", include("apps.sites.urls")),
    path("api/v1/downloads/", include("apps.file_download.urls")),
    path("api/v1/seo/", include("apps.seo.urls")),
    path("api/v1/obfuscator/", include("apps.obfuscator.urls")),
    path("api/v1/search/", include("apps.search.urls")),
    path("api/v1/", include("apps.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    # Front-facing SEO endpoints (no /api/v1/ prefix, easy for crawlers)
    path("sitemap.xml", include("apps.seo.urls")),
    path("rss.xml", include("apps.seo.urls")),
]

# Theme-aware front-end serving (multi-site) — handled by nginx in prod
# Development: `python manage.py serve_themes` uses sites.urls_front
