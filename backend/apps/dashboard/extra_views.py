"""Extra dashboard endpoints (v42-v52 consolidated)."""
from __future__ import annotations
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.account.permissions import CanEditSystem


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def dispatch_alerts(request):
    """v42: manually trigger alert check + dispatch."""
    from .alert_dispatcher import check_and_dispatch_alerts
    return Response(check_and_dispatch_alerts())


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, CanEditSystem])
def archive_chapters(request):
    """v44: archive old chapters to cold storage."""
    from apps.novel.archive import archive_old_chapters
    days = int(request.data.get("days", 365))
    dry = bool(request.data.get("dry_run", False))
    return Response(archive_old_chapters(days=days, dry_run=dry))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def source_health(request):
    """v45: crawler source health report."""
    from apps.crawler_rules.health_monitor import source_health_report
    source_id = request.query_params.get("source_id")
    days = int(request.query_params.get("days", 7))
    return Response(source_health_report(
        source_id=int(source_id) if source_id else None, days=days))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def audit_chapter_content(request):
    """v46: audit chapter content for banned keywords."""
    from apps.content_cleaner.audit import audit_chapter
    from apps.novel.models import Chapter
    chapter_id = request.data.get("chapter_id")
    if not chapter_id:
        return Response({"error": "chapter_id required"}, status=400)
    try:
        ch = Chapter.objects.get(pk=chapter_id)
    except Chapter.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    return Response(audit_chapter(ch))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, CanEditSystem])
def fill_covers(request):
    """v47: generate placeholder covers for books without one."""
    from apps.novel.cover_filler import fill_missing_covers
    limit = int(request.data.get("limit", 100))
    return Response(fill_missing_covers(limit=limit))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def generate_report(request):
    """v48: generate task execution report."""
    from apps.crawler_tasks.report import generate_task_report
    from apps.crawler_tasks.models import CrawlerTask
    task_id = request.data.get("task_id")
    fmt = request.data.get("format", "txt")
    try:
        task = CrawlerTask.objects.get(pk=task_id)
    except CrawlerTask.DoesNotExist:
        return Response({"error": "task not found"}, status=404)
    path = generate_task_report(task, format=fmt)
    return Response({"report_path": str(path), "format": fmt})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def smart_schedule(request):
    """v50: suggest best time to run a task."""
    from apps.crawler_tasks.smart_scheduler import suggest_best_time
    from apps.crawler_tasks.models import CrawlerTask
    task_id = request.query_params.get("task_id")
    try:
        task = CrawlerTask.objects.get(pk=task_id)
    except CrawlerTask.DoesNotExist:
        return Response({"error": "task not found"}, status=404)
    return Response(suggest_best_time(task))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def slow_queries(request):
    """v52: list recent slow queries."""
    from .slow_query_monitor import get_slow_queries
    limit = int(request.query_params.get("limit", 50))
    return Response({"queries": get_slow_queries(limit)})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, CanEditSystem])
def clear_slow_queries(request):
    """v52: clear slow query log."""
    from .slow_query_monitor import clear_slow_queries as clear
    clear()
    return Response({"status": "cleared"})
