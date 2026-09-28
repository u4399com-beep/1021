"""Per-domain rate limiter (v55) — prevent hammering a single source site."""
from __future__ import annotations
import time
from urllib.parse import urlparse
from django.core.cache import cache


def _domain_key(domain: str) -> str:
    return f"ratelimit:domain:{domain}"


def _domain_last_request_key(domain: str) -> str:
    return f"ratelimit:domain:last:{domain}"


def acquire_domain_slot(url: str, min_interval: float = 1.0) -> bool:
    """Check if enough time has passed since the last request to this domain.
    
    Returns True if we can proceed, False if we need to wait.
    """
    domain = urlparse(url).netloc
    if not domain:
        return True
    key = _domain_last_request_key(domain)
    last = cache.get(key, 0)
    now = time.time()
    if now - last < min_interval:
        return False
    cache.set(key, now, timeout=3600)
    return True


def get_domain_wait_time(url: str, min_interval: float = 1.0) -> float:
    """Return how many seconds to wait before the next request to this domain."""
    domain = urlparse(url).netloc
    if not domain:
        return 0
    key = _domain_last_request_key(domain)
    last = cache.get(key, 0)
    now = time.time()
    wait = min_interval - (now - last)
    return max(0, wait)


def domain_stats(domain: str) -> dict:
    """Return rate limit stats for a domain."""
    key = _domain_last_request_key(domain)
    last = cache.get(key, 0)
    now = time.time()
    return {
        "domain": domain,
        "last_request_ago_s": round(now - last, 1) if last else None,
        "requests_in_window": cache.get(_domain_key(domain), 0),
    }
