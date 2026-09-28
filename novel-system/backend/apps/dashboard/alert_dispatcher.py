"""Alert dispatcher (v42) — automatically push system health alerts to webhooks."""
import time
from django.core.cache import cache
from loguru import logger


_LAST_ALERT_KEY = "dashboard:last_alert_ts"


def check_and_dispatch_alerts():
    """Run health check + push any new alerts via webhooks.

    Called periodically by celery beat (every 5 minutes).
    Returns: {alerts: [...], dispatched: int}
    """
    from .health import _alert_status, _cpu_usage, _memory_usage, _disk_usage, _queue_depth, _db_connection_check, _redis_check
    metrics = {
        "cpu_percent": _cpu_usage(),
        "memory": _memory_usage(),
        "disk": _disk_usage(),
        "queue": _queue_depth(),
        "db": _db_connection_check(),
        "redis": _redis_check(),
    }
    alerts = _alert_status(metrics)
    if not alerts:
        return {"alerts": [], "dispatched": 0}

    # Throttle: only send each alert once per 10 minutes
    last_ts = cache.get(_LAST_ALERT_KEY, {})
    now = time.time()
    new_alerts = []
    for a in alerts:
        key = f"{a.get('metric')}:{a.get('level')}"
        if last_ts.get(key, 0) < now - 600:  # 10 min
            new_alerts.append(a)
            last_ts[key] = now
    cache.set(_LAST_ALERT_KEY, last_ts, timeout=3600)

    if not new_alerts:
        return {"alerts": alerts, "dispatched": 0, "throttled": True}

    # Dispatch via webhooks
    try:
        from apps.webhooks.engine import dispatch_event
        result = dispatch_event("system.error", {
            "message": f"系统告警 ({len(new_alerts)} 项)",
            "alerts": new_alerts,
        })
        return {"alerts": new_alerts, "dispatched": result.get("sent", 0)}
    except Exception as e:
        logger.warning(f"alert dispatch failed: {e!r}")
        return {"alerts": new_alerts, "dispatched": 0, "error": repr(e)}
