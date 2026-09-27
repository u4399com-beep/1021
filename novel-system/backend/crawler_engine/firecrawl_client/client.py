"""Firecrawl client wrapper.

Firecrawl is a hosted scraping service that handles JS rendering, anti-bot,
and content extraction. We wrap it here so:

  1. If `firecrawl-py` is not installed, this tier is skipped gracefully.
  2. The API key is pulled from `settings.CRAWLER.FIRECRAWL_API_KEY`.
  3. The result is normalized to always return HTML (`html` field preferred,
     otherwise `markdown` rendered back to HTML).
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(settings.CRAWLER.get("FIRECRAWL_API_KEY", ""))


def _get_client():
    """Lazy import — fail gracefully if firecrawl-py is not installed."""
    try:
        from firecrawl import FirecrawlApp  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "firecrawl-py is not installed. "
            "Run `pip install firecrawl-py` to enable the Firecrawl tier."
        ) from e
    api_key = settings.CRAWLER.get("FIRECRAWL_API_KEY", "")
    api_url = settings.CRAWLER.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v1")
    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY not configured in settings.CRAWLER")
    return FirecrawlApp(api_key=api_key, api_url=api_url)


def scrape_url(url: str, *, formats: list[str] | None = None, wait_for: int = 2000) -> dict[str, Any]:
    """Scrape a single URL via Firecrawl.

    Returns the raw Firecrawl response dict.
    """
    client = _get_client()
    formats = formats or ["html", "markdown"]
    params = {"formats": formats, "waitFor": wait_for}
    result = client.scrape_url(url, params=params)
    if not result:
        raise RuntimeError(f"firecrawl: empty response for {url}")
    if isinstance(result, dict) and result.get("success") is False:
        raise RuntimeError(f"firecrawl: {result.get('error', 'unknown error')}")
    # Normalize: some Firecrawl SDK versions return dict directly, some return object
    if not isinstance(result, dict):
        result = getattr(result, "__dict__", {}) or {}
    return result


def scrape_html(url: str, *, wait_for: int = 2000) -> str:
    """Scrape and return only the HTML payload (fallback to rendered markdown)."""
    result = scrape_url(url, formats=["html"], wait_for=wait_for)
    if "html" in result and result["html"]:
        return result["html"]
    if "data" in result and isinstance(result["data"], dict):
        html = result["data"].get("html")
        if html:
            return html
    # Last resort: render markdown to basic HTML
    md = result.get("markdown") or (result.get("data") or {}).get("markdown", "")
    if md:
        import markdown
        return markdown.markdown(md)
    raise RuntimeError(f"firecrawl: no html/markdown in response for {url}")


def crawl_site(url: str, *, limit: int = 50) -> list[dict[str, Any]]:
    """Crawl a whole site (used for batch discovery)."""
    client = _get_client()
    result = client.crawl_url(url, params={"limit": limit, "scrapeOptions": {"formats": ["html"]}})
    if isinstance(result, dict) and result.get("success") is False:
        raise RuntimeError(f"firecrawl crawl: {result.get('error')}")
    return result.get("data", []) if isinstance(result, dict) else result


def map_site(url: str) -> list[str]:
    """Fast URL discovery on a site (no scraping, just sitemap-style listing)."""
    client = _get_client()
    result = client.map_url(url)
    if isinstance(result, dict) and result.get("success") is False:
        raise RuntimeError(f"firecrawl map: {result.get('error')}")
    return result.get("links", []) if isinstance(result, dict) else result
