"""Multi-level cache (v66) — Redis + local memory + ETag."""
from __future__ import annotations
import hashlib
from django.core.cache import cache
from django.http import HttpResponse


_LOCAL_CACHE = {}  # In-process LRU (simple dict, capped)
_LOCAL_CAP = 200


def _etag_key(cache_key: str) -> str:
    return f"{cache_key}:etag"


def get_cached(key: str, local_fallback: bool = True):
    """Get from Redis first, then local memory."""
    # Level 1: local memory
    if local_fallback and key in _LOCAL_CACHE:
        entry = _LOCAL_CACHE[key]
        return entry["value"]
    # Level 2: Redis
    val = cache.get(key)
    if val is not None:
        # Promote to local
        _set_local(key, val)
        return val
    return None


def set_cached(key: str, value, ttl: int = 300) -> None:
    """Set in both Redis + local memory."""
    cache.set(key, value, timeout=ttl)
    _set_local(key, value)


def _set_local(key: str, value) -> None:
    if len(_LOCAL_CACHE) >= _LOCAL_CAP:
        # Simple eviction: remove oldest (first key)
        first_key = next(iter(_LOCAL_CACHE))
        del _LOCAL_CACHE[first_key]
    _LOCAL_CACHE[key] = {"value": value}


def compute_etag(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def check_etag(request, content: str) -> HttpResponse | None:
    """Return 304 if ETag matches, else None."""
    etag = compute_etag(content)
    if request.headers.get("If-None-Match") == etag:
        return HttpResponse(status=304, headers={"ETag": etag})
    return None


def cache_stats() -> dict:
    return {
        "local_cache_size": len(_LOCAL_CACHE),
        "local_cache_cap": _LOCAL_CAP,
    }
