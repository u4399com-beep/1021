"""反反爬资源池 — UA / Cookie / 代理。

UA 池 / Cookie 池基于数据库表，便于后台管理。代理池可对接第三方服务。
"""
from __future__ import annotations

import random
import threading
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


def get_user_agent() -> str:
    """Return a random UA — try DB-backed UA pool first."""
    cached = cache.get("uas_pool")
    if cached:
        return random.choice(cached)
    return random.choice(DEFAULT_UAS)


def get_cookie() -> Optional[dict]:
    """Return a random cookie dict — try DB-backed cookie pool first."""
    cached = cache.get("cookies_pool")
    if cached:
        return random.choice(cached)
    return None


def get_proxy() -> Optional[str]:
    """Return a proxy URL — pulls from DB / env. Returns None if no proxy."""
    cached = cache.get("proxy_pool")
    if cached:
        return random.choice(cached)
    from django.conf import settings
    return settings.CRAWLER.get("PLAYWRIGHT_PROXY") or None
