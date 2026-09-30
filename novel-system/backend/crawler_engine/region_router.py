"""Smart region selection for Hyperbrowser sessions.

Goal: when crawling a CN-hosted site (e.g., cunshu.la), use Hyperbrowser's
'cn' region to get CN-residential IPs (avoid geo-blocking).
For US sites, use 'us' region. For unknown, use 'auto'.

Strategy:
  - Maintain a host → region mapping (manual override possible)
  - Fallback to TLD heuristic (.cn → cn, .jp → asia, .com → auto, etc.)
  - Fallback to geolocation API (optional, lazy)

Usage:
    from crawler_engine.region_router import pick_region_for
    region = pick_region_for("https://www.cunshu.la/library.php")
    session = get_hyperbrowser_session(region=region)
"""

from urllib.parse import urlparse

from django.core.cache import cache


# TLD → region fallback map
_TLD_REGION_MAP = {
    # China
    ".cn": "cn",
    ".com.cn": "cn",
    # Hong Kong / Taiwan / Macao
    ".hk": "asia",
    ".tw": "asia",
    ".mo": "asia",
    # Japan / Korea
    ".jp": "asia",
    ".kr": "asia",
    # India
    ".in": "in",
    # Brazil
    ".br": "br",
    # European common TLDs
    ".de": "eu", ".fr": "eu", ".it": "eu", ".es": "eu",
    ".nl": "eu", ".be": "eu", ".se": "eu", ".no": "eu",
    ".fi": "eu", ".dk": "eu", ".at": "eu", ".ch": "eu",
    ".pl": "eu", ".cz": "eu", ".ru": "eu", ".uk": "eu",
    # North America
    ".us": "us",
    ".ca": "us",
    ".mx": "us",
    # Default for .com / .net / .org / .info — assume US
    ".com": "us",
    ".net": "us",
    ".org": "us",
    ".info": "us",
    ".io": "us",
    ".dev": "us",
}


# User-overridable host → region overrides
# Format: {"cunshu.la": "cn", "example.jp": "asia"}
# Stored in Django cache (persistent via Redis), editable via admin API.
_HOST_OVERRIDES_CACHE_KEY = "hyperbrowser:host_region_overrides"


def get_host_overrides() -> dict[str, str]:
    return cache.get(_HOST_OVERRIDES_CACHE_KEY, {}) or {}


def set_host_override(host: str, region: str) -> None:
    overrides = get_host_overrides()
    overrides[host] = region
    cache.set(_HOST_OVERRIDES_CACHE_KEY, overrides, timeout=None)


def clear_host_override(host: str) -> None:
    overrides = get_host_overrides()
    overrides.pop(host, None)
    cache.set(_HOST_OVERRIDES_CACHE_KEY, overrides, timeout=None)


def pick_region_for(url_or_host: str) -> str:
    """Return the best Hyperbrowser region for a given URL or hostname.

    Priority:
      1. Manual override (per-host)
      2. TLD heuristic
      3. 'auto' fallback
    """
    # Normalize to host
    if "://" in url_or_host:
        host = urlparse(url_or_host).netloc
    else:
        host = url_or_host
    host = host.lower().strip()
    # Strip port if any
    if ":" in host:
        host = host.split(":")[0]
    # Strip leading www. for matching
    if host.startswith("www."):
        host_no_www = host[4:]
    else:
        host_no_www = host

    # 1. Manual override — try host, then host_no_www
    overrides = get_host_overrides()
    if host in overrides:
        return overrides[host]
    if host_no_www in overrides:
        return overrides[host_no_www]

    # 2. TLD heuristic
    # Sort TLDs by length descending so ".com.cn" matches before ".cn"
    for tld in sorted(_TLD_REGION_MAP.keys(), key=len, reverse=True):
        if host.endswith(tld):
            return _TLD_REGION_MAP[tld]

    # 3. Default
    return "auto"


def diagnostics() -> dict:
    """Return current state for admin UI."""
    return {
        "host_overrides": get_host_overrides(),
        "tld_map_entries": len(_TLD_REGION_MAP),
        "regions_available": ["auto", "us", "eu", "asia", "cn", "in", "br"],
    }
