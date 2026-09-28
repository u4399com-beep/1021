"""API rate limiting (v101 fix) — atomic Redis ops + trusted proxy check."""
from __future__ import annotations

import time
from typing import Callable

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse


def _key(scope: str, ip: str) -> str:
    return f"ratelimit:{scope}:{ip}"


def _is_rate_limited_atomic(scope: str, ip: str, rate: int, per: int) -> tuple[bool, int]:
    """v101 fix: Use Django's cache.add (atomic) for initial key creation,
    then cache.incr (atomic) for counting. Avoid race conditions.
    """
    cache_key = _key(scope, ip)
    # Atomic add — returns True if key was created (didn't exist)
    created = cache.add(cache_key, 1, timeout=per)
    if created:
        return False, 0
    # Key exists — atomic increment
    try:
        current = cache.incr(cache_key)
    except ValueError:
        # Key expired between add and incr — recreate
        cache.set(cache_key, 1, timeout=per)
        current = 1
    if current > rate:
        return True, per
    return False, 0


def get_client_ip(request: HttpRequest) -> str:
    """v101 fix: Only trust X-Forwarded-For from configured trusted proxies."""
    remote_addr = request.META.get("REMOTE_ADDR", "0.0.0.0")
    trusted_proxies = getattr(settings, "TRUSTED_PROXIES", [])
    if trusted_proxies and remote_addr in trusted_proxies:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            # Take the LAST IP in chain (closest to our proxy), not the first
            # The first IP could be attacker-controlled
            ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            if ips:
                return ips[-1]
    return remote_addr


def get_matching_rule(path: str) -> tuple[str | None, dict | None]:
    rules = getattr(settings, "RATE_LIMIT_RULES", {}) or {}
    best_scope = None
    best_len = -1
    for scope, rule in rules.items():
        if path.startswith(scope) and len(scope) > best_len:
            best_scope = scope
            best_len = len(scope)
    if best_scope is None:
        return None, None
    return best_scope, rules[best_scope]


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path
        if not path.startswith("/api/"):
            return self.get_response(request)
        scope, rule = get_matching_rule(path)
        if not scope or not rule:
            return self.get_response(request)
        ip = get_client_ip(request)
        limited, retry_after = _is_rate_limited_atomic(scope, ip, rule["rate"], rule["per"])
        if limited:
            from rest_framework.response import Response
            response = Response(
                {"error": "rate_limited", "detail": f"超过访问限制：每 {rule['per']} 秒 {rule['rate']} 次",
                 "retry_after": retry_after},
                status=429,
            )
            response["Retry-After"] = str(retry_after)
            response["X-RateLimit-Scope"] = scope
            response["X-RateLimit-Limit"] = str(rule["rate"])
            return response
        return self.get_response(request)


def diagnostics() -> dict:
    rules = getattr(settings, "RATE_LIMIT_RULES", {}) or {}
    return {"rules_count": len(rules), "rules": rules}
