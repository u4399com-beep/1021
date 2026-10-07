"""iv8 代理池集成 (v317) — 住宅 IP 轮换 + TLS 指纹伪装。

iv8 (Ivanti/IPVanish-style) 代理池服务集成:
- 通过 API 获取住宅 IP 列表
- 自动轮换 IP（每次请求不同 IP）
- 支持 HTTP/HTTPS/SOCKS5 代理
- TLS 指纹在代理层面伪装
- 与 CloakBrowser（浏览器层）互补: iv8=网络层, CloakBrowser=浏览器层

配置 (.env):
    IV8_API_KEY=your-api-key
    IV8_API_URL=https://api.iv8proxy.com/v1/proxies
    IV8_PROXY_TYPE=residential  # residential|datacenter|mobile
    IV8_COUNTRY=CN  # CN|US|JP|...
"""
from __future__ import annotations

import os
import random
import time
from typing import Optional
from loguru import logger
from django.core.cache import cache


_IV8_CACHE_KEY = "iv8:proxy_pool"
_IV8_CACHE_TTL = 300  # 5 minutes


def _get_iv8_config() -> dict:
    from django.conf import settings
    return {
        "api_key": os.environ.get("IV8_API_KEY", ""),
        "api_url": os.environ.get("IV8_API_URL", "https://api.iv8proxy.com/v1/proxies"),
        "proxy_type": os.environ.get("IV8_PROXY_TYPE", "residential"),
        "country": os.environ.get("IV8_COUNTRY", ""),
        "enabled": bool(os.environ.get("IV8_API_KEY", "")),
    }


def is_iv8_enabled() -> bool:
    return _get_iv8_config()["enabled"]


def fetch_proxy_list() -> list[dict]:
    """Fetch a fresh list of proxies from iv8 API."""
    import httpx
    config = _get_iv8_config()
    if not config["enabled"]:
        return []

    try:
        params = {
            "api_key": config["api_key"],
            "type": config["proxy_type"],
            "count": 20,  # fetch 20 proxies at once
        }
        if config["country"]:
            params["country"] = config["country"]

        r = httpx.get(config["api_url"], params=params, timeout=15)
        if r.status_code != 200:
            logger.warning(f"iv8: API returned {r.status_code}")
            return []

        data = r.json()
        proxies = []
        for item in data.get("proxies", []):
            proxies.append({
                "ip": item.get("ip", ""),
                "port": item.get("port", 0),
                "protocol": item.get("protocol", "http"),
                "username": item.get("username", ""),
                "password": item.get("password", ""),
                "country": item.get("country", ""),
            })

        cache.set(_IV8_CACHE_KEY, proxies, timeout=_IV8_CACHE_TTL)
        logger.info(f"iv8: fetched {len(proxies)} proxies")
        return proxies

    except Exception as e:
        logger.warning(f"iv8: fetch failed: {e!r}")
        return []


def get_proxy() -> Optional[str]:
    """Get a random proxy URL from the iv8 pool.

    Returns: "http://user:pass@ip:port" or None
    """
    if not is_iv8_enabled():
        return None

    proxies = cache.get(_IV8_CACHE_KEY)
    if not proxies:
        proxies = fetch_proxy_list()
        if not proxies:
            return None

    proxy = random.choice(proxies)
    proto = proxy.get("protocol", "http")
    auth = ""
    if proxy.get("username"):
        auth = f"{proxy['username']}:{proxy['password']}@"

    return f"{proto}://{auth}{proxy['ip']}:{proxy['port']}"


def get_proxy_for_playwright() -> Optional[dict]:
    """Get proxy config for Playwright context.

    Returns: {"server": "http://ip:port", "username": "...", "password": "..."} or None
    """
    if not is_iv8_enabled():
        return None

    proxies = cache.get(_IV8_CACHE_KEY)
    if not proxies:
        proxies = fetch_proxy_list()
        if not proxies:
            return None

    proxy = random.choice(proxies)
    return {
        "server": f"{proxy.get('protocol', 'http')}://{proxy['ip']}:{proxy['port']}",
        "username": proxy.get("username", ""),
        "password": proxy.get("password", ""),
    }


def diagnostics() -> dict:
    """Return iv8 proxy pool diagnostics."""
    config = _get_iv8_config()
    proxies = cache.get(_IV8_CACHE_KEY, [])
    return {
        "enabled": config["enabled"],
        "proxy_type": config["proxy_type"],
        "country": config["country"],
        "cached_proxies": len(proxies),
    }
