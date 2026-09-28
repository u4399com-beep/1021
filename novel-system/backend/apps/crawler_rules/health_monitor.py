"""Crawler source health monitor (v45) — track success rate per source."""
from __future__ import annotations
from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone
from apps.crawler_rules.models import CrawlerSource
from apps.crawler_tasks.models import CrawlerTask, CrawlerTaskLog


def source_health_report(source_id: int = None, days: int = 7) -> dict:
    """Return health metrics for a source (or all sources)."""
    since = timezone.now() - timedelta(days=days)
    if source_id:
        sources = CrawlerSource.objects.filter(id=source_id)
    else:
        sources = CrawlerSource.objects.all()
    report = []
    for src in sources:
        tasks = CrawlerTask.objects.filter(
            list_rule__source=src, finished_at__gte=since
        )
        total = tasks.count()
        success = tasks.filter(status="done").count()
        failed = tasks.filter(status="error").count()
        report.append({
            "source_id": src.id, "source_name": src.name, "source_host": src.host,
            "enabled": src.enabled,
            "total_tasks": total, "success": success, "failed": failed,
            "success_rate": round(success / total * 100, 1) if total else 0,
            "avg_duration_s": 0,  # placeholder
        })
    return {"sources": report, "days": days, "since": since.isoformat()}
