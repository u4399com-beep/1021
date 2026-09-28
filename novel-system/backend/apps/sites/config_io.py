"""Site config export/import (v94)."""
import json
from apps.sites.models import Site, Theme

def export_site_config(site_id: int) -> dict:
    """Export all config for a site as JSON."""
    try:
        site = Site.objects.get(pk=site_id)
    except Site.DoesNotExist:
        return {"error": "not found"}
    return {
        "format": "novel-system-site-v1",
        "site": {
            "host": site.host, "name": site.name,
            "theme_code": site.theme.code,
            "site_title": site.site_title, "site_description": site.site_description,
            "site_keywords": site.site_keywords,
            "robots_txt": site.robots_txt, "sitemap_enabled": site.sitemap_enabled,
            "geo_region": site.geo_region, "geo_lang": site.geo_lang,
            "canonical_domain": site.canonical_domain, "offset": site.offset,
            "head_inject": site.head_inject, "body_inject": site.body_inject,
        },
    }

def import_site_config(config: dict) -> dict:
    """Import a site config."""
    if config.get("format") != "novel-system-site-v1":
        return {"error": "unsupported format"}
    data = config["site"]
    theme = Theme.objects.filter(code=data.get("theme_code", "simple_reading")).first()
    site, created = Site.objects.update_or_create(
        host=data["host"],
        defaults={**data, "theme": theme},
    )
    return {"site_id": site.id, "host": site.host, "created": created}
