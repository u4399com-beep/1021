"""Consolidated dashboard endpoints (v172) — merged from extra_views/v54/v69."""
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



@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def ai_generate_list_rule(request):
    from apps.crawler_rules.ai.rule_generator import generate_list_rule
    html = request.data.get("html", "")
    return Response(generate_list_rule(html))



@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def ai_generate_book_rule(request):
    from apps.crawler_rules.ai.rule_generator import generate_book_rule
    html = request.data.get("html", "")
    return Response(generate_book_rule(html))



@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def ai_generate_chapter_rule(request):
    from apps.crawler_rules.ai.rule_generator import generate_chapter_rule
    html = request.data.get("html", "")
    return Response(generate_chapter_rule(html))

# v70: Advertising


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def ad_slots_for_page(request):
    from apps.sites.advertising import get_ads_for_page
    host = request.query_params.get("host", request.get_host())
    page_type = request.query_params.get("page_type", "home")
    theme = request.query_params.get("theme", "")
    return Response({"ads": get_ads_for_page(host, page_type, theme)})

# v71-v72: Membership + Payments


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def reader_register(request):
    from apps.account.membership import ReaderProfile
    username = request.data.get("username", "")
    if not username:
        return Response({"error": "username required"}, status=400)
    if ReaderProfile.objects.filter(username=username).exists():
        return Response({"error": "username taken"}, status=400)
    reader = ReaderProfile.objects.create(
        username=username,
        email=request.data.get("email", ""),
        nickname=request.data.get("nickname", username),
    )
    return Response({"id": reader.id, "username": reader.username}, status=201)



@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def reader_profile(request, reader_id: int):
    from apps.account.membership import ReaderProfile
    try:
        reader = ReaderProfile.objects.get(pk=reader_id, is_active=True)
    except ReaderProfile.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    return Response({
        "id": reader.id, "username": reader.username, "nickname": reader.nickname,
        "membership_level": reader.membership_level, "is_vip": reader.is_vip,
        "coins": reader.coins,
    })



@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def create_payment_order(request):
    from apps.account.payments import create_order
    from apps.account.membership import ReaderProfile
    reader_id = request.data.get("reader_id")
    product_type = request.data.get("product_type", "vip_monthly")
    amount = float(request.data.get("amount", 30))
    try:
        reader = ReaderProfile.objects.get(pk=reader_id)
    except ReaderProfile.DoesNotExist:
        return Response({"error": "reader not found"}, status=404)
    order = create_order(reader, product_type, amount)
    return Response({"order_no": order.order_no, "amount": str(order.amount), "status": order.status})

# v74: Distributed cluster


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def cluster_status(request):
    from apps.crawler_tasks.distributed import cluster_stats
    return Response(cluster_stats())

# v75: Migrator


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def import_books(request):
    from apps.novel.migrator import import_books_from_json
    data = request.data.get("books", request.data)
    overwrite = bool(request.data.get("overwrite", False))
    return Response(import_books_from_json(data, overwrite=overwrite))

# v76: WS notifications


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def recent_notifications(request):
    from apps.dashboard.ws_notify import get_recent_notifications
    return Response({"notifications": get_recent_notifications()})

# v77: Preset library


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def rule_presets(request):
    from apps.crawler_rules.preset_library import list_presets, get_preset
    name = request.query_params.get("name")
    if name:
        return Response(get_preset(name) or {"error": "not found"})
    return Response({"presets": list_presets()})

# v78: Reading themes


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def reading_themes(request):
    from apps.novel.reading_prefs import THEMES
    names = {"default": "白天", "sepia": "护眼黄", "night": "夜间", "green": "护眼绿", "high_contrast": "高对比"}
    return Response({"themes": [{"key": k, "name": names.get(k, k), **v} for k, v in THEMES.items()]})

# v80: Ratings


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def rate_book(request):
    from apps.novel.ratings import BookRating, update_book_aggregate_rating
    from apps.account.membership import ReaderProfile
    from apps.novel.models import Book
    reader_id = request.data.get("reader_id")
    book_id = request.data.get("book_id")
    score = int(request.data.get("score", 5))
    if score < 1 or score > 5:
        return Response({"error": "score must be 1-5"}, status=400)
    try:
        reader = ReaderProfile.objects.get(pk=reader_id)
        book = Book.objects.get(pk=book_id)
    except Exception:
        return Response({"error": "reader or book not found"}, status=404)
    rating, _ = BookRating.objects.update_or_create(
        reader=reader, book=book,
        defaults={"score": score, "review": request.data.get("review", "")},
    )
    update_book_aggregate_rating(book)
    return Response({"rating_id": rating.id, "score": score, "book_rating": book.rating})

# v81: Tag extraction


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def extract_tags(request):
    from apps.novel.tag_extractor import extract_keywords
    text = request.data.get("text", "")
    top_n = int(request.data.get("top_n", 10))
    return Response({"keywords": extract_keywords(text, top_n)})

# v82: Benchmark


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def run_benchmark(request):
    from apps.dashboard.benchmark import benchmark_url
    url = request.data.get("url", "")
    concurrent = int(request.data.get("concurrent", 10))
    total = int(request.data.get("total", 100))
    if not url:
        return Response({"error": "url required"}, status=400)
    return Response(benchmark_url(url, concurrent, total))



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



