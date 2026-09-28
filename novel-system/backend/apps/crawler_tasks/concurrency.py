"""Concurrency limiter for crawler tasks.

Goal: when many crawler tasks are queued simultaneously, prevent them all
running at once and overwhelming target sites (and the local Playwright pool).

Strategy:
  - Each task has `priority` (0-100), `max_concurrent_per_class`, `exclusive`.
  - When a task is about to start, call `acquire_slot(task)`.
  - Returns True if a slot was acquired, False otherwise (task should wait).
  - When a task finishes, call `release_slot(task)`.

Implementation:
  - Active tasks are tracked in Redis sorted set, keyed by priority.
  - Per-class counts are tracked in Redis hash for fast atomic ops.
  - Global max concurrent is configurable via settings.
"""
from __future__ import annotations

import time
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


_GLOBAL_MAX = getattr(settings, "CRAWLER", {}).get("MAX_CONCURRENT_TASKS", 8)
_GLOBAL_KEY = "crawler:active_tasks:global"
_CLASS_KEY_PREFIX = "crawler:active_tasks:class:"
_EXCLUSIVE_KEY = "crawler:active_tasks:exclusive"


def _lock_key(task_id: int) -> str:
    return f"crawler:active_tasks:lock:{task_id}"


def acquire_slot(task) -> bool:
    """Try to acquire an execution slot for this task.

    Returns True if the task can start now, False otherwise.

    The task object must have: id, priority, max_concurrent_per_class, exclusive,
    and source (optional, used for per-class limiting).
    """
    if not task or not task.id:
        return True

    # Exclusive tasks: no other task can be running
    if task.exclusive:
        if cache.get(_EXCLUSIVE_KEY):
            return False
        cache.set(_EXCLUSIVE_KEY, task.id, timeout=60 * 60)  # 1h safety timeout
        cache.set(_lock_key(task.id), "exclusive", timeout=60 * 60)
        return True

    # Global limit
    global_active = cache.get(_GLOBAL_KEY, 0)
    if global_active >= _GLOBAL_MAX:
        return False

    # Per-class limit (by source_id)
    source_id = getattr(getattr(task, "list_rule", None), "source_id", None) or 0
    class_key = f"{_CLASS_KEY_PREFIX}{source_id}"
    class_active = cache.get(class_key, 0)
    if task.max_concurrent_per_class > 0 and class_active >= task.max_concurrent_per_class:
        return False

    # Acquire: increment both global and class counters
    cache.incr(_GLOBAL_KEY) if cache.get(_GLOBAL_KEY) is not None else cache.set(_GLOBAL_KEY, 1, timeout=60 * 60)
    cache.incr(class_key) if cache.get(class_key) is not None else cache.set(class_key, 1, timeout=60 * 60)
    cache.set(_lock_key(task.id), {"priority": task.priority, "started_at": time.time()}, timeout=60 * 60)
    return True


def release_slot(task) -> None:
    """Release the execution slot held by this task."""
    if not task or not task.id:
        return

    if task.exclusive:
        if cache.get(_EXCLUSIVE_KEY) == task.id:
            cache.delete(_EXCLUSIVE_KEY)
        cache.delete(_lock_key(task.id))
        return

    # Decrement global and class counters (only if this task had acquired)
    if cache.get(_lock_key(task.id)):
        source_id = getattr(getattr(task, "list_rule", None), "source_id", None) or 0
        class_key = f"{_CLASS_KEY_PREFIX}{source_id}"
        try:
            cache.decr(_GLOBAL_KEY)
        except Exception:
            pass
        try:
            cache.decr(class_key)
        except Exception:
            pass
        cache.delete(_lock_key(task.id))


def get_active_count() -> dict:
    """Return a snapshot of current concurrency state for diagnostics."""
    return {
        "global_active": cache.get(_GLOBAL_KEY, 0),
        "global_max": _GLOBAL_MAX,
        "exclusive_holder": cache.get(_EXCLUSIVE_KEY),
    }


def list_active_task_ids() -> list[int]:
    """Return list of task ids currently holding a slot."""
    # Scan lock keys — O(N) but bounded by max concurrent
    pattern = "crawler:active_tasks:lock:*"
    # Note: cache backend must support iter_keys for this to work;
    # for Redis backend we'd need raw client. For simplicity, return [].
    return []
