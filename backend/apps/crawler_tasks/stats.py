"""Task execution history aggregator — computes statistics across all runs.

Used by the dashboard / task history panel to surface:
  - Total runs per day/week
  - Success rate trends
  - Average execution time
  - Most active tasks (top N by run count)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.crawler_tasks.models import CrawlerTask, CrawlerTaskLog


def overall_stats() -> dict[str, Any]:
    """Compute high-level stats across all tasks."""
    qs = CrawlerTask.objects.all()
    total = qs.count()
    by_status = list(qs.values("status").annotate(count=Count("id")))
    return {
        "total_tasks": total,
        "by_status": {item["status"]: item["count"] for item in by_status},
        "running_now": qs.filter(status="running").count(),
        "completed_today": qs.filter(
            status="done",
            finished_at__gte=timezone.now() - timedelta(days=1),
        ).count(),
        "failed_today": qs.filter(
            status="error",
            finished_at__gte=timezone.now() - timedelta(days=1),
        ).count(),
    }


def runs_per_day(days: int = 30) -> list[dict[str, Any]]:
    """Return total runs + success/failed counts per day for the last N days."""
    since = timezone.now() - timedelta(days=days)
    qs = CrawlerTask.objects.filter(finished_at__gte=since)
    by_day = defaultdict(lambda: {"total": 0, "success": 0, "failed": 0})
    for t in qs:
        if not t.finished_at:
            continue
        key = t.finished_at.strftime("%Y-%m-%d")
        by_day[key]["total"] += 1
        if t.status == "done":
            by_day[key]["success"] += 1
        elif t.status == "error":
            by_day[key]["failed"] += 1
    return [
        {"date": day, **stats}
        for day, stats in sorted(by_day.items())
    ]


def top_active_tasks(limit: int = 10) -> list[dict[str, Any]]:
    """Return the N most-run tasks."""
    qs = CrawlerTask.objects.annotate(
        total_processed=Sum("processed_items"),
        total_success=Sum("success_items"),
    ).order_by("-schedule_run_count")[:limit]
    return [
        {
            "id": t.id, "name": t.name,
            "schedule_run_count": t.schedule_run_count,
            "total_processed": t.processed_items,
            "total_success": t.success_items,
            "status": t.status,
            "success_rate": (t.success_items / t.processed_items * 100)
                if t.processed_items > 0 else 0,
        }
        for t in qs
    ]


def recent_log_summary(task_id: int | None = None, hours: int = 24, limit: int = 50) -> dict:
    """Aggregate recent log levels."""
    since = timezone.now() - timedelta(hours=hours)
    qs = CrawlerTaskLog.objects.filter(created_at__gte=since)
    if task_id:
        qs = qs.filter(task_id=task_id)
    by_level = list(qs.values("level").annotate(count=Count("id")))
    recent = list(qs.order_by("-id")[:limit].values("id", "level", "message", "url", "created_at", "task_id"))
    return {
        "by_level": {item["level"]: item["count"] for item in by_level},
        "recent": recent,
    }
