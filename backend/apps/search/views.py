"""Full-text search API using PostgreSQL pg_trgm (v26).

Provides fast fuzzy search across books, authors, chapters, and tags.

Endpoints:
  GET /api/v1/search/?q=斗破苍穹&limit=20
  GET /api/v1/search/books/?q=...
  GET /api/v1/search/authors/?q=...
  GET /api/v1/search/chapters/?q=...
  GET /api/v1/search/tags/?q=...
  GET /api/v1/search/suggest/?q=...  (autocomplete)
"""
from __future__ import annotations

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, QuerySet
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.novel.models import Author, Book, Chapter, Tag
from apps.novel.serializers import (
    AuthorSerializer, BookListSerializer, ChapterListSerializer, TagSerializer,
)


class SearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "limit"
    max_page_size = 100


def _paginate(qs: QuerySet, request):
    paginator = SearchPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator, page


def _fuzzy_search_books(q: str) -> QuerySet[Book]:
    qs = Book.objects.filter(is_published=True, is_deleted=False)
    if not q:
        return qs.none()
    qs1 = qs.annotate(
        similarity=TrigramSimilarity("title", q) + TrigramSimilarity("intro", q) * 0.3
    ).filter(similarity__gt=0.1).order_by("-similarity")
    if qs1.count() < 10:
        qs2 = qs.filter(
            Q(title__icontains=q) |
            Q(intro__icontains=q) |
            Q(tags__name__icontains=q) |
            Q(author__name__icontains=q)
        ).distinct()
        merged_ids = list(qs1.values_list("id", flat=True)) + list(qs2.values_list("id", flat=True))
        seen, merged = set(), []
        for bid in merged_ids:
            if bid not in seen:
                seen.add(bid)
                merged.append(bid)
                if len(merged) >= 50:
                    break
        return Book.objects.filter(id__in=merged).order_by("-rating", "-updated_at")
    return qs1


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def search_all(request):
    q = request.query_params.get("q", "").strip()
    if not q:
        return Response({"error": "q required"}, status=400)
    books = _fuzzy_search_books(q)[:10]
    authors = Author.objects.annotate(
        similarity=TrigramSimilarity("name", q)
    ).filter(similarity__gt=0.1).order_by("-similarity")[:5]
    tags = Tag.objects.annotate(
        similarity=TrigramSimilarity("name", q)
    ).filter(similarity__gt=0.1).order_by("-similarity")[:5]
    chapters = Chapter.objects.filter(title__icontains=q)[:5]
    return Response({
        "query": q,
        "books": BookListSerializer(books, many=True).data,
        "authors": AuthorSerializer(authors, many=True).data,
        "tags": TagSerializer(tags, many=True).data,
        "chapters": ChapterListSerializer(chapters, many=True).data,
        "total": len(books) + len(authors) + len(tags) + len(chapters),
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def search_books(request):
    q = request.query_params.get("q", "").strip()
    if not q:
        return Response({"error": "q required"}, status=400)
    qs = _fuzzy_search_books(q)
    paginator, page = _paginate(qs, request)
    return Response({
        "results": BookListSerializer(page, many=True).data,
        "count": paginator.page.paginator.count,
        "page": paginator.page.number,
        "pages": paginator.page.paginator.num_pages,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def search_authors(request):
    q = request.query_params.get("q", "").strip()
    if not q:
        return Response({"error": "q required"}, status=400)
    qs = Author.objects.annotate(
        similarity=TrigramSimilarity("name", q)
    ).filter(similarity__gt=0.1).order_by("-similarity")
    paginator, page = _paginate(qs, request)
    return Response({
        "results": AuthorSerializer(page, many=True).data,
        "count": paginator.page.paginator.count,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def search_chapters(request):
    q = request.query_params.get("q", "").strip()
    if not q:
        return Response({"error": "q required"}, status=400)
    qs = Chapter.objects.filter(
        Q(title__icontains=q) | Q(content__icontains=q)
    )[:200]
    return Response({
        "results": ChapterListSerializer(qs, many=True).data,
        "count": qs.count(),
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def search_tags(request):
    q = request.query_params.get("q", "").strip()
    if not q:
        return Response({"error": "q required"}, status=400)
    qs = Tag.objects.annotate(
        similarity=TrigramSimilarity("name", q)
    ).filter(similarity__gt=0.1).order_by("-similarity")[:20]
    return Response({
        "results": TagSerializer(qs, many=True).data,
        "count": qs.count(),
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def search_suggest(request):
    q = request.query_params.get("q", "").strip()
    if not q or len(q) < 2:
        return Response({"suggestions": []})
    book_qs = Book.objects.filter(
        is_published=True, is_deleted=False, title__icontains=q
    ).order_by("-rating")[:7]
    suggestions = [
        {"type": "book", "title": b.title, "slug": b.slug, "url": f"/book/{b.slug}"}
        for b in book_qs
    ]
    author_qs = Author.objects.filter(name__icontains=q)[:3]
    suggestions += [
        {"type": "author", "title": a.name, "slug": a.name, "url": f"/search?q={a.name}"}
        for a in author_qs
    ]
    return Response({"suggestions": suggestions, "query": q})
