"""Dashboard analytics (v36) — weekly/monthly stats with chart-friendly output."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from django.db.models import Count
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.crawler_tasks.models import CrawlerTask
from apps.novel.models import Book, Chapter


def _period_since(period: str) -> timezone.datetime:
    now = timezone.now()
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    if period == "quarter":
        return now - timedelta(days=90)
    if period == "year":
        return now - timedelta(days=365)
    return now - timedelta(days=30)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def books_added(request):
    period = request.query_params.get("period", "month")
    since = _period_since(period)
    qs = Book.objects.filter(created_at__gte=since)
    if period == "week":
        trunc = TruncDate("created_at")
    elif period == "year":
        trunc = TruncMonth("created_at")
    else:
        trunc = TruncWeek("created_at")
    grouped = qs.annotate(period=trunc).values("period").annotate(count=Count("id")).order_by("period")
    labels = []
    counts = []
    for g in grouped:
        labels.append(g["period"].strftime("%Y-%m-%d"))
        counts.append(g["count"])
    return Response({
        "labels": labels,
        "datasets": [{"label": "新增书籍", "data": counts, "backgroundColor": "#1e88e5"}],
        "total_in_period": sum(counts),
        "period": period,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def tasks_completed(request):
    period = request.query_params.get("period", "month")
    since = _period_since(period)
    qs = CrawlerTask.objects.filter(finished_at__gte=since)
    if period == "week":
        trunc = TruncDate("finished_at")
    elif period == "year":
        trunc = TruncMonth("finished_at")
    else:
        trunc = TruncWeek("finished_at")
    grouped = qs.annotate(period=trunc).values("period", "status").annotate(count=Count("id")).order_by("period")
    labels_set = set()
    status_counts = defaultdict(lambda: defaultdict(int))
    for g in grouped:
        date_str = g["period"].strftime("%Y-%m-%d") if g["period"] else "?"
        labels_set.add(date_str)
        status_counts[g["status"]][date_str] = g["count"]
    labels = sorted(labels_set)
    datasets = []
    for status in ("done", "error", "stopped"):
        datasets.append({
            "label": status,
            "data": [status_counts[status].get(d, 0) for d in labels],
            "backgroundColor": {"done": "#4caf50", "error": "#f44336", "stopped": "#ff9800"}[status],
        })
    return Response({"labels": labels, "datasets": datasets, "period": period})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def success_rate_trend(request):
    period = request.query_params.get("period", "month")
    since = _period_since(period)
    qs = CrawlerTask.objects.filter(finished_at__gte=since, status__in=["done", "error"])
    if period == "week":
        trunc = TruncDate("finished_at")
    elif period == "year":
        trunc = TruncMonth("finished_at")
    else:
        trunc = TruncWeek("finished_at")
    grouped = qs.annotate(period=trunc).values("period", "status").annotate(count=Count("id")).order_by("period")
    labels_set = []
    status_counts = defaultdict(lambda: defaultdict(int))
    for g in grouped:
        date_str = g["period"].strftime("%Y-%m-%d") if g["period"] else "?"
        if date_str not in labels_set:
            labels_set.append(date_str)
        status_counts[g["status"]][date_str] = g["count"]
    labels_set.sort()
    rates = []
    for d in labels_set:
        done = status_counts["done"][d]
        err = status_counts["error"][d]
        total = done + err
        rates.append(round((done / total * 100) if total else 0, 1))
    return Response({
        "labels": labels_set,
        "datasets": [{"label": "成功率(%)", "data": rates, "borderColor": "#4caf50"}],
        "period": period,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def top_books(request):
    metric = request.query_params.get("metric", "views")
    limit = int(request.query_params.get("limit", 10))
    qs = Book.objects.filter(is_published=True, is_deleted=False)
    if metric == "views":
        qs = qs.order_by("-view_count")
    elif metric == "chapters":
        qs = qs.order_by("-chapter_count")
    elif metric == "rating":
        qs = qs.order_by("-rating")
    else:
        qs = qs.order_by("-word_count")
    books = qs[:limit]
    return Response({
        "labels": [b.title[:20] for b in books],
        "datasets": [{
            "label": {"views": "浏览量", "chapters": "章节数", "rating": "评分", "words": "字数"}.get(metric, metric),
            "data": [getattr(b, {"views": "view_count", "chapters": "chapter_count", "rating": "rating", "words": "word_count"}.get(metric, "view_count")) for b in books],
        }],
        "metric": metric,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def storage_usage(request):
    import os
    from pathlib import Path
    from django.conf import settings
    media_root = Path(settings.MEDIA_ROOT)
    breakdown = {"covers": 0, "chapters": 0, "downloads": 0, "sitemaps": 0, "logs": 0, "other": 0}
    total = 0
    if media_root.exists():
        for root, dirs, files in os.walk(media_root):
            for f in files:
                p = Path(root) / f
                size = p.stat().st_size
                total += size
                rel = str(p.relative_to(media_root))
                if "covers" in rel: breakdown["covers"] += size
                elif "chapters" in rel: breakdown["chapters"] += size
                elif "downloads" in rel: breakdown["downloads"] += size
                elif "sitemaps" in rel: breakdown["sitemaps"] += size
                elif "logs" in rel: breakdown["logs"] += size
                else: breakdown["other"] += size
    return Response({
        "total_bytes": total,
        "total_mb": round(total / 1024 / 1024, 2),
        "breakdown": {k: {"bytes": v, "mb": round(v / 1024 / 1024, 2)} for k, v in breakdown.items()},
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def summary(request):
    return Response({
        "books": {
            "total": Book.objects.filter(is_deleted=False).count(),
            "published": Book.objects.filter(is_deleted=False, is_published=True).count(),
            "ongoing": Book.objects.filter(status="ongoing").count(),
            "completed": Book.objects.filter(status="completed").count(),
        },
        "chapters": {"total": Chapter.objects.count()},
        "tasks": {
            "total": CrawlerTask.objects.count(),
            "running": CrawlerTask.objects.filter(status="running").count(),
            "scheduled": CrawlerTask.objects.filter(schedule_enabled=True).count(),
        },
    })
