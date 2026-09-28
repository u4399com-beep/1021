"""v69-v82 API endpoints."""
from __future__ import annotations
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


# v69: AI rule generation
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
