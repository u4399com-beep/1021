"""Site-level caching control for HTML responses.

Goal: balance obfuscation (every render should be unique) with cache hits
(browsers/CDN should be able to cache static assets and even some HTML).

Strategy:
  - Static assets (.css, .js, images): always cache (immutable, versioned)
  - List pages: cache N seconds at CDN level (e.g. 60s) but vary-by-render
                on the server to keep obfuscation unique per origin request
  - Chapter pages: cache longer (e.g. 300s) since chapters rarely change
  - Book detail pages: cache 600s

Cache headers are controlled per-Site via Site.cache_* fields.
"""
from __future__ import annotations

from django.http import HttpResponse
from django.utils.cache import add_never_cache_headers, patch_cache_control, patch_vary_headers


# Defaults (in seconds) if Site doesn't override
DEFAULT_CACHE_TIMES = {
    "home": 60,         # 1 minute
    "category": 300,    # 5 minutes
    "book_detail": 600, # 10 minutes
    "chapter": 1800,    # 30 minutes
    "rss": 600,
    "sitemap": 3600,
}


def apply_cache_headers(response: HttpResponse, site, page_type: str) -> HttpResponse:
    """Apply per-site Cache-Control headers based on page_type.

    Args:
        response: the HTTP response to modify
        site: Site object (may be None — then default to no-cache)
        page_type: one of "home", "category", "book_detail", "chapter",
                   "rss", "sitemap", "static"
    """
    if site is None:
        # No site = no caching at all
        add_never_cache_headers(response)
        return response

    # Get cache duration from site or defaults
    cache_field = f"cache_{page_type}_seconds"
    duration = getattr(site, cache_field, None)
    if duration is None:
        duration = DEFAULT_CACHE_TIMES.get(page_type, 60)

    if page_type == "static":
        # Static assets — long cache
        patch_cache_control(response, max_age=86400, public=True, immutable=True)
    elif duration <= 0:
        # Explicitly disabled
        add_never_cache_headers(response)
    else:
        patch_cache_control(response, max_age=duration, public=True)
        # Also vary by User-Agent to avoid serving obfuscated-for-mobile to desktop users
        patch_vary_headers(response, ["User-Agent"])

    return response
