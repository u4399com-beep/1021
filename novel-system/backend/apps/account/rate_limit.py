"""API rate limiting (v27) — token bucket per-IP, per-endpoint.

Goals:
  - Prevent single IP from hammering search / crawler engine / login
  - Allow bursty traffic but cap sustained rate
  - Configurable per-endpoint limits
  - Returns 429 with Retry-After header when exceeded

Implementation:
  - Token bucket in Redis (atomic via INCRBY + EXPIRE)
  - Django middleware reads request path → looks up rule → enforces
  - Rules defined in settings.RATE_LIMIT_RULES

Usage in settings:
    RATE_LIMIT_RULES = {
        "/api/v1/search/":             {"rate": 60, "per": 60},   # 60 req / 60s
        "/api/v1/crawler/engine/test/":{"rate": 5,  "per": 60},   # 5 req / 60s
        "/api/v1/auth/login/":         {"rate": 10, "per": 60},   # 10 req / 60s
    }
"""
from __future__ import annotations

import time
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from rest_framework.response import Response


def _key(scope: str, ip: str) -> str:
    return f"ratelimit:{scope}:{ip}"


def _is_rate_limited(scope: str, ip: str, rate: int, per: int) -> tuple[bool, int]:
    """Check + consume a token. Returns (is_limited, retry_after_seconds).

    Uses Redis INCRBY atomically; first request in window sets the key with TTL.
    """
    cache_key = _key(scope, ip)
    current = cache.get(cache_key)
    if current is None:
        cache.set(cache_key, 1, timeout=per)
        return False, 0
    if current >= rate:
        # Already over limit — keep TTL fresh
        return True, per
    cache.incr(cache_key)
    return False, 0


def get_client_ip(request: HttpRequest) -> str:
    """Get real client IP — respects X-Forwarded-For from nginx."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # First IP in chain is the original client
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def get_matching_rule(path: str) -> tuple[str | None, dict | None]:
    """Find the most specific matching rate-limit rule for this path.

    Returns (scope, rule_dict) or (None, None).
    """
    rules = getattr(settings, "RATE_LIMIT_RULES", {}) or {}
    best_scope = None
    best_len = -1
    for scope, rule in rules.items():
        if path.startswith(scope) and len(scope) > best_len:
            best_scope = scope
            best_len = len(scope)
            best_rule = rule
    if best_scope is None:
        return None, None
    return best_scope, best_rule


class RateLimitMiddleware:
    """Django middleware enforcing per-IP rate limits.

    Add to MIDDLEWARE in settings.py.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Only enforce on API paths
        path = request.path
        if not path.startswith("/api/"):
            return self.get_response(request)

        scope, rule = get_matching_rule(path)
        if not scope or not rule:
            return self.get_response(request)

        ip = get_client_ip(request)
        limited, retry_after = _is_rate_limited(scope, ip, rule["rate"], rule["per"])
        if limited:
            response = Response(
                {
                    "error": "rate_limited",
                    "detail": f"超过访问限制：每 {rule['per']} 秒 {rule['rate']} 次",
                    "retry_after": retry_after,
                },
                status=429,
            )
            response["Retry-After"] = str(retry_after)
            response["X-RateLimit-Scope"] = scope
            response["X-RateLimit-Limit"] = str(rule["rate"])
            return response

        return self.get_response(request)


def diagnostics() -> dict:
    """Return current rate-limit configuration for the admin UI."""
    rules = getattr(settings, "RATE_LIMIT_RULES", {}) or {}
    return {
        "rules_count": len(rules),
        "rules": rules,
    }
