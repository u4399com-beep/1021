"""WebSocket notification (v76) — real-time push to admin UI.

Uses Django Channels (requires channels + daphne in production).
For simplicity, this provides a Redis pub/sub based notification system
that can be consumed by any WebSocket gateway.
"""
from __future__ import annotations
import json
from django.core.cache import cache


_NOTIFY_CHANNEL = "ws:notify"


def publish_notification(event_type: str, data: dict) -> None:
    """Publish a notification event to the Redis channel."""
    msg = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
    # Redis pub/sub — use cache as a simple alternative
    cache.set(f"{_NOTIFY_CHANNEL}:latest", msg, timeout=3600)
    # Also append to a list for polling clients
    history = cache.get(f"{_NOTIFY_CHANNEL}:history", [])
    history.insert(0, {"type": event_type, "data": data, "ts": __import__("time").time()})
    cache.set(f"{_NOTIFY_CHANNEL}:history", history[:100], timeout=3600)


def get_recent_notifications(limit: int = 20) -> list[dict]:
    """Return recent notifications (for polling clients)."""
    return cache.get(f"{_NOTIFY_CHANNEL}:history", [])[:limit]


# Event types
def notify_task_started(task): publish_notification("task.started", {"id": task.id, "name": task.name})
def notify_task_done(task): publish_notification("task.done", {"id": task.id, "name": task.name, "success": task.success_items})
def notify_task_error(task, error): publish_notification("task.error", {"id": task.id, "name": task.name, "error": error[:200]})
def notify_system_alert(alert): publish_notification("system.alert", alert)
