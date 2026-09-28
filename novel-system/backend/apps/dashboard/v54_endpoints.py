"""v54-v67 API endpoints."""
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def check_duplicates(request):
    """v54: find duplicate books."""
    from apps.novel.dedup import find_duplicates
    from apps.novel.models import Book
    book_id = request.data.get("book_id")
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    return Response({"duplicates": find_duplicates(book)})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def merge_duplicates(request):
    """v54: merge duplicate books."""
    from apps.novel.dedup import merge_duplicates
    from apps.novel.models import Book
    primary_id = request.data.get("primary_id")
    secondary_ids = request.data.get("secondary_ids", [])
    try:
        primary = Book.objects.get(pk=primary_id)
    except Book.DoesNotExist:
        return Response({"error": "primary not found"}, status=404)
    return Response(merge_duplicates(primary, secondary_ids))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def domain_rate(request):
    """v55: domain rate limit stats."""
    from apps.crawler_tasks.domain_rate_limiter import domain_stats
    from urllib.parse import urlparse
    url = request.query_params.get("url", "")
    if not url:
        return Response({"error": "url required"}, status=400)
    return Response(domain_stats(urlparse(url).netloc))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def score_chapter_content(request):
    """v56: score chapter quality."""
    from apps.novel.quality_scorer import score_chapter
    content = request.data.get("content", "")
    return Response(score_chapter(content))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def save_rule_version(request):
    """v57: save a rule version snapshot."""
    from apps.crawler_rules.versioning import save_version
    from apps.crawler_rules.models import CrawlerRule
    rule_id = request.data.get("rule_id")
    try:
        rule = CrawlerRule.objects.get(pk=rule_id)
    except CrawlerRule.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    ver = save_version(rule, changed_by=request.user.username, reason=request.data.get("reason", ""))
    return Response({"version_number": ver.version_number, "rule_id": rule_id})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def rollback_rule(request):
    """v57: rollback rule to a version."""
    from apps.crawler_rules.versioning import rollback_to_version
    from apps.crawler_rules.models import CrawlerRule
    rule_id = request.data.get("rule_id")
    version = int(request.data.get("version", 0))
    try:
        rule = CrawlerRule.objects.get(pk=rule_id)
    except CrawlerRule.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    ok = rollback_to_version(rule, version)
    return Response({"ok": ok, "version": version})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def predict_eta(request):
    """v58: predict task execution time."""
    from apps.crawler_tasks.eta_predictor import predict_eta
    from apps.crawler_tasks.models import CrawlerTask
    task_id = request.query_params.get("task_id")
    try:
        task = CrawlerTask.objects.get(pk=task_id)
    except CrawlerTask.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    return Response(predict_eta(task))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def db_pool_diagnostics(request):
    """v59: DB connection pool diagnostics."""
    from config.db_pool import diagnostics
    return Response(diagnostics())


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def cache_diagnostics(request):
    """v60/v66: cache diagnostics."""
    from apps.api.cache_middleware import cache_diagnostics as api_diag
    from apps.sites.multilevel_cache import cache_stats
    return Response({"api_cache": api_diag(), "multilevel": cache_stats()})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def segment_content(request):
    """v61: segment content."""
    from apps.novel.segmenter import segment_stats
    content = request.data.get("content", "")
    max_chars = int(request.data.get("max_chars", 3000))
    return Response(segment_stats(content, max_chars))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def export_rules(request):
    """v62: export rules as JSON."""
    from apps.crawler_rules.io import export_rules
    from django.http import JsonResponse
    source_id = request.query_params.get("source_id")
    pkg = export_rules(int(source_id) if source_id else None)
    from django.utils import timezone
    pkg["exported_at"] = timezone.now().isoformat()
    return Response(pkg)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def import_rules(request):
    """v62: import rules from JSON."""
    from apps.crawler_rules.io import import_rules
    return Response(import_rules(request.data, overwrite=bool(request.data.get("overwrite", False))))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def traffic_summary(request):
    """v63: traffic stats."""
    from apps.sites.traffic_stats import traffic_summary
    host = request.query_params.get("host", "")
    days = int(request.query_params.get("days", 7))
    if not host:
        return Response({"error": "host required"}, status=400)
    return Response(traffic_summary(host, days))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def auto_adjust_priorities(request):
    """v64: auto adjust task priorities."""
    from apps.crawler_tasks.auto_priority import adjust_priorities
    return Response(adjust_priorities())


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def detect_updates(request):
    """v65: detect new chapters for a book."""
    from apps.novel.update_detector import detect_new_chapters
    from apps.novel.models import Book
    book_id = request.data.get("book_id")
    remote_chapters = request.data.get("remote_chapters", [])
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    return Response(detect_new_chapters(book, remote_chapters))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def integrity_check(request):
    """v67: data integrity check."""
    from apps.novel.integrity_check import check_integrity
    return Response(check_integrity())


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def repair_counts(request):
    """v67: repair stale counts."""
    from apps.novel.integrity_check import repair_stale_counts
    return Response(repair_stale_counts())
