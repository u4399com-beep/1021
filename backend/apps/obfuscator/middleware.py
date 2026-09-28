"""Middleware that applies per-site obfuscation to HTML responses.

Skips:
  - Admin pages (/admin/, /django-admin/, /api/)
  - AJAX / JSON responses
  - Static / media files
  - Responses with non-HTML content-type
  - Responses with status != 200
  - Sites without an enabled ObfuscationProfile
"""
from __future__ import annotations

import re

from django.http import HttpRequest, HttpResponse

from .engine import apply_obfuscation


_SKIP_PREFIXES = (
    "/admin/",
    "/django-admin/",
    "/api/",
    "/static/",
    "/media/",
    "/WAF/",
    "/.well-known/",
)


class ObfuscatorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Skip non-200 quickly
        if response.status_code != 200:
            return response

        # Skip admin / api / static paths
        path = request.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return response

        # Only process HTML responses
        ctype = response.get("Content-Type", "")
        if "html" not in ctype.lower():
            return response

        # Skip if response is streaming or has no content
        if response.streaming or not response.content:
            return response

        # Look up the site for this host
        from apps.sites.models import Site
        host = request.get_host().split(":")[0]
        try:
            site = Site.objects.get(host=host, is_active=True)
        except Site.DoesNotExist:
            return response

        # Apply obfuscation
        try:
            html = response.content.decode(response.charset or "utf-8", errors="replace")
            obfuscated = apply_obfuscation(html, site=site)
            response.content = obfuscated.encode(response.charset or "utf-8")
            # Update Content-Length header
            if "Content-Length" in response:
                response["Content-Length"] = len(response.content)
        except Exception as e:
            # Never break a response due to obfuscation failure
            import logging
            logging.getLogger(__name__).warning(f"obfuscation failed: {e!r}")

        return response
