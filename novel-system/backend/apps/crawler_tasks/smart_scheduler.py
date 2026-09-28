"""Smart scheduler (v50) — suggest best time to run based on historical success."""
from __future__ import annotations
from datetime import timedelta
from django.db.models import Avg, Count
from django.utils import timezone
from apps.crawler_tasks.models import CrawlerTask


def suggest_best_time(task: CrawlerTask, lookback_days: int = 30) -> dict:
    """Analyze historical runs of similar tasks and suggest the best hour to run.

    Returns: {best_hour: 0-23, best_hour_success_rate: float, by_hour: [...]}
    """
    since = timezone.now() - timedelta(days=lookback_days)
    # Find similar tasks (same source)
    similar = CrawlerTask.objects.filter(
        list_rule__source=task.list_rule.source if task.list_rule else None,
        finished_at__gte=since,
    ).exclude(status__in=["draft", "queued", "running", "paused"])

    by_hour = {h: {"total": 0, "success": 0} for h in range(24)}
    for t in similar:
        if not t.finished_at:
            continue
        hour = t.finished_at.hour
        by_hour[hour]["total"] += 1
        if t.status == "done":
            by_hour[hour]["success"] += 1

    # Find hour with highest success rate (min 3 samples)
    best_hour = 3  # default: 3 AM (low traffic)
    best_rate = 0
    for h, stats in by_hour.items():
        if stats["total"] >= 3:
            rate = stats["success"] / stats["total"]
            if rate > best_rate:
                best_rate = rate
                best_hour = h

    return {
        "best_hour": best_hour,
        "best_hour_success_rate": round(best_rate * 100, 1),
        "by_hour": [
            {"hour": h, "total": s["total"], "success": s["success"],
             "rate": round(s["success"] / s["total"] * 100, 1) if s["total"] else 0}
            for h, s in by_hour.items()
        ],
        "suggested_cron": f"0 {best_hour} * * *",
    }
