"""Mobile API (v73) — dedicated endpoints for mobile apps."""
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class MobilePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "per_page"
    max_page_size = 50


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def mobile_home(request):
    """Mobile homepage — compact book list + categories."""
    from apps.novel.models import Book, Category
    from apps.novel.serializers import BookListSerializer
    
    # Featured books (top 10 by rating)
    featured = Book.objects.filter(is_published=True, is_deleted=False).order_by("-rating")[:10]
    # Latest books
    latest = Book.objects.filter(is_published=True, is_deleted=False).order_by("-updated_at")[:20]
    # Categories
    categories = Category.objects.filter(is_active=True, parent__isnull=True).values("id", "name", "slug")
    
    return Response({
        "featured": BookListSerializer(featured, many=True).data,
        "latest": BookListSerializer(latest, many=True).data,
        "categories": list(categories),
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def mobile_book_detail(request, book_id: int):
    """Mobile book detail — compact format."""
    from apps.novel.models import Book
    from apps.novel.serializers import BookDetailSerializer
    try:
        book = Book.objects.get(pk=book_id, is_deleted=False)
    except Book.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    return Response(BookDetailSerializer(book).data)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def mobile_chapter_list(request, book_id: int):
    """Mobile chapter list — paginated."""
    from apps.novel.models import Chapter
    from apps.novel.serializers import ChapterListSerializer
    
    qs = Chapter.objects.filter(book_id=book_id).order_by("order_index")
    paginator = MobilePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(ChapterListSerializer(page, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def mobile_chapter_content(request, book_id: int, chapter_order: int):
    """Mobile chapter content — text-only (strip heavy HTML)."""
    from apps.novel.models import Chapter
    try:
        ch = Chapter.objects.get(book_id=book_id, order_index=chapter_order)
    except Chapter.DoesNotExist:
        return Response({"error": "not found"}, status=404)
    
    # Strip heavy tags for mobile
    import re
    content = ch.content or ""
    content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
    content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL)
    content = re.sub(r"<img[^>]*>", "", content)  # no images on mobile
    
    return Response({
        "book_id": book_id, "chapter_order": chapter_order,
        "title": ch.title, "content": content,
        "word_count": ch.word_count,
        "has_prev": Chapter.objects.filter(book_id=book_id, order_index__lt=chapter_order).exists(),
        "has_next": Chapter.objects.filter(book_id=book_id, order_index__gt=chapter_order).exists(),
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def mobile_search(request):
    """Mobile search — lightweight."""
    from apps.novel.models import Book
    from apps.novel.serializers import BookListSerializer
    q = request.query_params.get("q", "").strip()
    if not q:
        return Response({"error": "q required"}, status=400)
    from django.db.models import Q
    qs = Book.objects.filter(
        is_published=True, is_deleted=False
    ).filter(
        Q(title__icontains=q) | Q(author__name__icontains=q) | Q(tags__name__icontains=q)
    ).distinct()[:20]
    return Response({"results": BookListSerializer(qs, many=True).data, "count": qs.count()})
