"""24-hour windowed success-rate aggregation for proxies.

Goal: track per-hour success/failure counts so we can detect proxies that
are good in some hours but bad in others (e.g., blocked during peak hours),
and route traffic accordingly.

Storage: Redis (per-proxy rolling 24h counters per hour bucket).

Schema:
  Key: proxy:hourly:{proxy_id}
  Value: hash map {hour_str: "success_count:failure_count", ...}
  TTL: 25 hours
"""

from datetime import datetime, timedelta

from django.core.cache import cache


def _hour_key(dt: datetime | None = None) -> str:
    dt = dt or datetime.now()
    return dt.strftime("%Y%m%d%H")


def _proxy_cache_key(proxy_id: int) -> str:
    return f"proxy:hourly:{proxy_id}"


def record_hourly(proxy_id: int, success: bool = True) -> None:
    """Increment the per-hour counter for a proxy."""
    key = _proxy_cache_key(proxy_id)
    hour = _hour_key()
    raw = cache.get(key, {})
    if not isinstance(raw, dict):
        raw = {}
    cur = raw.get(hour, "0:0")
    s, f = (int(x) for x in cur.split(":"))
    if success:
        s += 1
    else:
        f += 1
    raw[hour] = f"{s}:{f}"
    cache.set(key, raw, timeout=25 * 3600)


def get_hourly_stats(proxy_id: int, hours: int = 24) -> dict[str, dict]:
    """Return per-hour stats for the last N hours."""
    key = _proxy_cache_key(proxy_id)
    raw = cache.get(key, {}) or {}
    now = datetime.now()
    result = {}
    for i in range(hours):
        hour_dt = now - timedelta(hours=hours - 1 - i)
        h = hour_dt.strftime("%Y%m%d%H")
        cur = raw.get(h, "0:0")
        s, f = (int(x) for x in cur.split(":"))
        total = s + f
        rate = (s / total) if total else 0
        result[hour_dt.strftime("%Y-%m-%d %H:00")] = {
            "hour": h,
            "success": s,
            "failure": f,
            "total": total,
            "success_rate": round(rate, 4),
        }
    return result


def get_windowed_success_rate(proxy_id: int, window_hours: int = 24) -> float:
    """Return success rate across the last N hours (0.0-1.0)."""
    stats = get_hourly_stats(proxy_id, hours=window_hours)
    total_s = sum(h["success"] for h in stats.values())
    total_f = sum(h["failure"] for h in stats.values())
    total = total_s + total_f
    return (total_s / total) if total else 0.0


def get_best_hours(proxy_id: int, hours: int = 24, top_n: int = 5) -> list[dict]:
    """Return the N hours with the highest success rate for this proxy."""
    stats = get_hourly_stats(proxy_id, hours=hours)
    ranked = sorted(
        stats.values(),
        key=lambda x: (x["success_rate"], x["total"]),
        reverse=True,
    )
    return ranked[:top_n]


def get_worst_hours(proxy_id: int, hours: int = 24, top_n: int = 3) -> list[dict]:
    """Return the N hours with the lowest success rate (non-zero sample)."""
    stats = get_hourly_stats(proxy_id, hours=hours)
    filtered = [s for s in stats.values() if s["total"] > 0]
    ranked = sorted(
        filtered,
        key=lambda x: (x["success_rate"], -x["total"]),
    )
    return ranked[:top_n]


# ------------------------------------------------------------------
# Per-hour rate limiter (v20)
# ------------------------------------------------------------------
def _rate_key(proxy_id: int, hour: str | None = None) -> str:
    hour = hour or _hour_key()
    return f"proxy:ratelimit:{proxy_id}:{hour}"


def try_acquire_request_slot(proxy_id: int, max_per_hour: int = 100) -> bool:
    """Bounded-rate acquire for a proxy.

    Returns True if a slot is available, False if the proxy has hit
    its hourly cap. Counter resets each hour.
    """
    key = _rate_key(proxy_id)
    current = cache.get(key, 0)
    if current >= max_per_hour:
        return False
    if cache.get(key) is None:
        cache.set(key, 1, timeout=3600)
    else:
        cache.incr(key)
    return True


def get_hourly_request_count(proxy_id: int) -> int:
    return cache.get(_rate_key(proxy_id), 0)
