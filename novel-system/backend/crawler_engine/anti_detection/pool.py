"""反反爬资源池 — UA / Cookie / 代理。

UA 池 / Cookie 池基于数据库表，便于后台管理。代理池可对接第三方服务
（Hyperbrowser 的 sessions 池或自维护代理 IP 池）。

ProxyPool 路由策略：
  - 若 Hyperbrowser 启用：自动选择一个 HyperbrowserProxy 池子，
    在 Playwright 中通过 CDP 连接 Hyperbrowser 的会话端点。
  - 否则：从 ProxyPool 表中按优先级+轮询取一个 HTTP/HTTPS 代理。
"""

import json
import random
import threading
import time
from typing import Optional

from django.core.cache import cache


# Default UA fallback — should be replaced by DB-driven pool in production
DEFAULT_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]

_DEFAULT_COOKIE_LOCK = threading.Lock()
_DEFAULT_COOKIES: list[dict] = []

# In-memory round-robin pointer for ProxyPool
_PROXY_RR = 0
_PROXY_LOCK = threading.Lock()


def get_user_agent() -> str:
    cached = cache.get("uas_pool")
    if cached:
        return random.choice(cached)
    return random.choice(DEFAULT_UAS)


def get_cookie() -> Optional[dict]:
    cached = cache.get("cookies_pool")
    if cached:
        return random.choice(cached)
    return None


# ------------------------------------------------------------------
# Proxy pool
# ------------------------------------------------------------------
def get_proxy() -> Optional[str]:
    """Return a proxy URL — try DB-backed ProxyPool first, fall back to env.

    Returns None if no proxy is configured.
    """
    global _PROXY_RR

    # Try the ProxyPool DB table first
    try:
        from apps.crawler.models import ProxyPool  # lazy import to avoid circular

        active = list(ProxyPool.objects.filter(is_active=True).order_by("-priority", "id"))
        if active:
            with _PROXY_LOCK:
                # Round-robin across active proxies
                proxy = active[_PROXY_RR % len(active)]
                _PROXY_RR += 1
            return proxy.url
    except Exception:
        pass

    cached = cache.get("proxy_pool")
    if cached:
        return random.choice(cached)
    from django.conf import settings
    return settings.CRAWLER.get("PLAYWRIGHT_PROXY") or None


# ------------------------------------------------------------------
# Hyperbrowser proxy pool management
# ------------------------------------------------------------------
_HYPERBROWSER_SESSION_CACHE_KEY = "hyperbrowser:sessions"
_HYPERBROWSER_SESSION_TTL = 90  # seconds — Hyperbrowser sessions last ~5min by default

# Available Hyperbrowser regions
HYPERBROWSER_REGIONS = ("auto", "us", "eu", "asia", "cn", "in", "br")


def get_hyperbrowser_session(region: str = "auto"):
    """Return a Hyperbrowser CDP URL (create or reuse a cached one).

    Args:
        region: one of HYPERBROWSER_REGIONS. Region routing allows targeting
                specific geographic IP pools — useful when source sites
                geo-block (e.g., a CN-hosted site may need asia/cn region).
    """
    import httpx
    from django.conf import settings

    api_key = settings.CRAWLER.get("HYPERBROWSER_API_KEY", "")
    if not api_key:
        raise RuntimeError("HYPERBROWSER_API_KEY not configured")

    # Check cache first — share sessions across worker processes
    cached = cache.get(_HYPERBROWSER_SESSION_CACHE_KEY)
    if cached and isinstance(cached, list) and cached:
        # Pick the LRU session that matches the requested region (or any if "auto")
        matching = [s for s in cached if s.get("region") == region or region == "auto"]
        pool = matching if matching else cached
        pool.sort(key=lambda s: s.get("last_used_at", 0))
        return pool[0]

    # Create a new session in the requested region
    create_url = "https://api.hyperbrowser.dev/v1/sessions"
    payload = {
        "sessionOptions": {
            "solve_captchas": True,
            "proxy": region if region != "auto" else "auto",
            "_stealth": True,
        }
    }
    r = httpx.post(
        create_url,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"hyperbrowser: create session failed: {r.status_code} {r.text}")
    data = r.json()
    cdp_url = data.get("cdpUrl") or data.get("wsEndpoint")
    if not cdp_url:
        raise RuntimeError("hyperbrowser: no cdpUrl in response")

    session = {
        "session_id": data.get("id") or data.get("sessionId"),
        "cdp_url": cdp_url,
        "region": data.get("region", region),
        "created_at": time.time(),
        "expires_at": time.time() + _HYPERBROWSER_SESSION_TTL,
        "last_used_at": time.time(),
    }
    _cache_session(session)
    return session


def _cache_session(session: dict) -> None:
    """Append a session to the in-cache pool, keeping at most 5 sessions."""
    cached = cache.get(_HYPERBROWSER_SESSION_CACHE_KEY) or []
    cached = [s for s in cached if s.get("expires_at", 0) > time.time()]
    cached.append(session)
    if len(cached) > 5:
        cached = cached[-5:]
    cache.set(_HYPERBROWSER_SESSION_CACHE_KEY, cached, _HYPERBROWSER_SESSION_TTL)


def list_hyperbrowser_sessions() -> list[dict]:
    """Return cached Hyperbrowser sessions (for diagnostics)."""
    cached = cache.get(_HYPERBROWSER_SESSION_CACHE_KEY) or []
    return [s for s in cached if s.get("expires_at", 0) > time.time()]


def release_hyperbrowser_session(session_id: str) -> None:
    """Mark a session as released (and optionally end it server-side)."""
    import httpx
    from django.conf import settings

    api_key = settings.CRAWLER.get("HYPERBROWSER_API_KEY", "")
    cached = cache.get(_HYPERBROWSER_SESSION_CACHE_KEY) or []
    cached = [s for s in cached if s.get("session_id") != session_id]
    cache.set(_HYPERBROWSER_SESSION_CACHE_KEY, cached, _HYPERBROWSER_SESSION_TTL)

    if api_key and session_id:
        try:
            httpx.delete(
                f"https://api.hyperbrowser.dev/v1/sessions/{session_id}",
                headers={"x-api-key": api_key},
                timeout=10,
            )
        except Exception:
            pass


def hyperbrowser_diagnostics() -> dict:
    """Return diagnostic info about Hyperbrowser config + active sessions."""
    from django.conf import settings

    api_key = settings.CRAWLER.get("HYPERBROWSER_API_KEY", "")
    sessions = list_hyperbrowser_sessions() if api_key else []
    return {
        "configured": bool(api_key),
        "active_sessions": len(sessions),
        "sessions": [
            {
                "session_id": s.get("session_id"),
                "region": s.get("region"),
                "expires_in_seconds": int(s.get("expires_at", 0) - time.time()),
            }
            for s in sessions
        ],
    }


def get_cookie_from_db(domain: str) -> dict | None:
    """v260: Get cookies from DB-backed CookiePool."""
    try:
        from apps.crawler.anti_detection_models import CookiePool
        from django.utils import timezone
        pool = CookiePool.objects.filter(
            site_domain=domain, is_active=True
        ).order_by('-use_count').first()
        if pool and (not pool.expires_at or pool.expires_at > timezone.now()):
            pool.use_count += 1
            pool.save(update_fields=['use_count'])
            return pool.cookies
    except Exception:
        pass
    return None
