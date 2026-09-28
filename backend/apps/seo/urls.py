from django.urls import path

from .views import (
    audit,
    regenerate_sitemaps,
    rss_book,
    rss_site,
    sitemap_view,
    theme_check,
)

app_name = "seo"

urlpatterns = [
    # Front-end facing
    path("sitemap.xml", sitemap_view, name="sitemap"),
    path("sitemap/<str:host>/sitemap.xml", sitemap_view, name="sitemap-host"),
    path("rss.xml", rss_site, name="rss-site"),
    path("rss/<str:host>/rss.xml", rss_site, name="rss-site-host"),
    path("book/<str:slug>/rss.xml", rss_book, name="rss-book"),

    # Admin API
    path("audit/", audit, name="audit-all"),
    path("audit/<int:site_id>/", audit, name="audit-one"),
    path("regenerate-sitemaps/", regenerate_sitemaps, name="regen-sitemaps"),
    path("theme-check/", theme_check, name="theme-check-all"),
    path("theme-check/<str:theme_code>/", theme_check, name="theme-check-one"),
]
