"""Export endpoints — books / tasks / chapters / generic."""
from __future__ import annotations

from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.novel.models import Book, Chapter
from apps.crawler_tasks.models import CrawlerTask

from .export_engine import (
    BOOK_FIELDS, TASK_FIELDS,
    export_books_csv, export_books_json,
    export_tasks_csv, export_tasks_json,
    export_queryset_csv, export_queryset_json,
)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def export_books(request):
    """GET /api/v1/export/books/?format=csv
    Optional filters: status, is_published, q
    """
    fmt = request.query_params.get("format", "csv").lower()
    qs = Book.objects.filter(is_deleted=False)
    if request.query_params.get("status"):
        qs = qs.filter(status=request.query_params.get("status"))
    if request.query_params.get("is_published"):
        qs = qs.filter(is_published=request.query_params.get("is_published").lower() in ("true", "1"))
    if request.query_params.get("q"):
        from django.db.models import Q
        q = request.query_params.get("q")
        qs = qs.filter(Q(title__icontains=q) | Q(intro__icontains=q))
    if fmt == "json":
        return export_books_json(qs)
    return export_books_csv(qs)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def export_tasks(request):
    """GET /api/v1/export/tasks/?format=csv
    Optional filters: status, mode, schedule_enabled
    """
    fmt = request.query_params.get("format", "csv").lower()
    qs = CrawlerTask.objects.all()
    if request.query_params.get("status"):
        qs = qs.filter(status=request.query_params.get("status"))
    if fmt == "json":
        return export_tasks_json(qs)
    return export_tasks_csv(qs)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def export_chapters(request):
    """GET /api/v1/export/chapters/?format=csv&book_id=1
    Optional filters: book_id, status
    """
    fmt = request.query_params.get("format", "csv").lower()
    qs = Chapter.objects.all()
    if request.query_params.get("book_id"):
        qs = qs.filter(book_id=int(request.query_params.get("book_id")))
    if request.query_params.get("status"):
        qs = qs.filter(status=request.query_params.get("status"))
    fields = ["id", "book_id", "title", "order_index", "status", "word_count",
              "fetched_at", "source_url"]
    if fmt == "json":
        return export_queryset_json(qs, fields, "chapters")
    return export_queryset_csv(qs, fields, "chapters")
