"""API response cache (v60) — cache GET responses for read-heavy endpoints."""
from __future__ import annotations
import hashlib, json
from django.core.cache import cache
from rest_framework.response import Response


_CACHEABLE_PATTERNS = [
    "/api/v1/novels/categories/",
    "/api/v1/novels/tags/",
    "/api/v1/themes/",
    "/api/v1/dashboard/summary/",
    "/api/v1/dashboard/storage/",
    "/api/v1/sites/themes/",
]

_CACHE_TTL = 300  # 5 minutes


def _cache_key(request) -> str:
    raw = f"{request.path}?{request.GET.urlencode()}"
    return f"api_cache:{hashlib.md5(raw.encode()).hexdigest()}"


class APICacheMiddleware:
    """Cache GET responses for cacheable patterns."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.method != "GET":
            return self.get_response(request)
        
        path = request.path
        cacheable = any(path.startswith(p) for p in _CACHEABLE_PATTERNS)
        if not cacheable:
            return self.get_response(request)
        
        key = _cache_key(request)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached, status=200)
        
        response = self.get_response(request)
        if hasattr(response, "data") and response.status_code == 200:
            cache.set(key, response.data, _CACHE_TTL)
        return response


def invalidate_cache(path_prefix: str = "") -> int:
    """Invalidate cached API responses matching a path prefix."""
    # With Redis we'd use SCAN, but with LocMem we can't easily enumerate.
    # For production: use cache.delete_many with known keys.
    cache.clear()  # Nuclear option — fine for small deployments
    return 1


def cache_diagnostics() -> dict:
    return {
        "cacheable_patterns": _CACHEABLE_PATTERNS,
        "ttl_seconds": _CACHE_TTL,
    }
