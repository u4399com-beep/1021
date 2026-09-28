"""Bookshelf sync + reading history (v88-v89)."""
from __future__ import annotations
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([AllowAny])
def get_bookshelf(request, reader_id: int):
    from apps.account.membership import Bookshelf
    items = Bookshelf.objects.filter(reader_id=reader_id).select_related("book")
    return Response({"bookshelf": [
        {"book_id": b.book_id, "title": b.book.title, "slug": b.book.slug,
         "last_read_chapter": b.last_read_chapter, "added_at": b.added_at.isoformat()}
        for b in items
    ]})

@api_view(["POST"])
@permission_classes([AllowAny])
def add_to_bookshelf(request):
    from apps.account.membership import Bookshelf
    from apps.novel.models import Book
    reader_id = request.data.get("reader_id")
    book_id = request.data.get("book_id")
    try:
        book = Book.objects.get(pk=book_id, is_deleted=False)
    except Book.DoesNotExist:
        return Response({"error": "book not found"}, status=404)
    item, created = Bookshelf.objects.get_or_create(reader_id=reader_id, book=book)
    return Response({"added": created, "book_id": book_id})

@api_view(["POST"])
@permission_classes([AllowAny])
def remove_from_bookshelf(request):
    from apps.account.membership import Bookshelf
    Bookshelf.objects.filter(
        reader_id=request.data.get("reader_id"),
        book_id=request.data.get("book_id")
    ).delete()
    return Response({"removed": True})

@api_view(["GET"])
@permission_classes([AllowAny])
def get_reading_history(request, reader_id: int):
    from apps.account.membership import ReadingHistory
    items = ReadingHistory.objects.filter(reader_id=reader_id).select_related("book")[:50]
    return Response({"history": [
        {"book_id": h.book_id, "title": h.book.title, "slug": h.book.slug,
         "chapter_order": h.chapter_order, "read_at": h.read_at.isoformat(),
         "duration": h.read_duration}
        for h in items
    ]})

@api_view(["POST"])
@permission_classes([AllowAny])
def update_reading_progress(request):
    from apps.account.membership import ReadingHistory, Bookshelf
    from django.utils import timezone
    reader_id = request.data.get("reader_id")
    book_id = request.data.get("book_id")
    chapter_order = int(request.data.get("chapter_order", 0))
    duration = int(request.data.get("duration", 0))
    # Update bookshelf last-read
    Bookshelf.objects.filter(reader_id=reader_id, book_id=book_id).update(
        last_read_chapter=chapter_order, last_read_at=timezone.now()
    )
    # Record history
    ReadingHistory.objects.create(
        reader_id=reader_id, book_id=book_id,
        chapter_order=chapter_order, read_duration=duration,
    )
    return Response({"updated": True})
