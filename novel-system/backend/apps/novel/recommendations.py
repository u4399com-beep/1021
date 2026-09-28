"""Recommendation system (v90) — based on reading history."""
from django.db.models import Q, Count
from apps.novel.models import Book, Tag, Category
from apps.account.membership import ReadingHistory

def recommend_for_reader(reader_id: int, limit: int = 10) -> list[dict]:
    """Recommend books based on reader's history — same categories/tags."""
    history = ReadingHistory.objects.filter(reader_id=reader_id).select_related("book")
    if not history.exists():
        # Cold start: return top-rated books
        return [{"id": b.id, "title": b.title, "slug": b.slug, "rating": b.rating,
                 "reason": "热门推荐"} for b in
                Book.objects.filter(is_published=True, is_deleted=False).order_by("-rating")[:limit]]
    # Collect categories + tags from history
    cat_ids, tag_ids = set(), set()
    for h in history[:20]:
        for c in h.book.categories.all():
            cat_ids.add(c.id)
        for t in h.book.tags.all():
            tag_ids.add(t.id)
    # Find books with matching categories or tags
    read_book_ids = set(history.values_list("book_id", flat=True))
    recommended = Book.objects.filter(
        is_published=True, is_deleted=False
    ).exclude(id__in=read_book_ids).filter(
        Q(categories__id__in=cat_ids) | Q(tags__id__in=tag_ids)
    ).distinct().annotate(
        match_count=Count("id")
    ).order_by("-match_count", "-rating")[:limit]
    return [{"id": b.id, "title": b.title, "slug": b.slug, "rating": b.rating,
             "reason": "基于您的阅读历史"} for b in recommended]
