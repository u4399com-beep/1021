"""Book rankings (v92)."""
from __future__ import annotations
from django.db.models import F
from apps.novel.models import Book

def get_ranking(metric: str = "views", limit: int = 50, period_days: int = 0) -> list[dict]:
    """Get book rankings by metric."""
    qs = Book.objects.filter(is_published=True, is_deleted=False)
    if metric == "views":
        qs = qs.order_by("-view_count")
    elif metric == "rating":
        qs = qs.order_by("-rating")
    elif metric == "chapters":
        qs = qs.order_by("-chapter_count")
    elif metric == "newest":
        qs = qs.order_by("-created_at")
    elif metric == "updated":
        qs = qs.order_by("-updated_at")
    elif metric == "words":
        qs = qs.order_by("-word_count")
    books = qs[:limit]
    return [{"rank": i+1, "id": b.id, "title": b.title, "slug": b.slug,
             "author": b.author.name if b.author else "", "rating": b.rating,
             "view_count": b.view_count, "chapter_count": b.chapter_count,
             "word_count": b.word_count, "status": b.status} for i, b in enumerate(books)]
