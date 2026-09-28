"""Sitemap priority auto-ranking (v84) — rank books by popularity in sitemap."""
from apps.novel.models import Book

def compute_priority(book: Book) -> str:
    """Compute sitemap priority 0.4-1.0 based on book popularity."""
    base = 0.5
    # Rating bonus (0-0.3)
    if book.rating and book.rating > 0:
        base += min(0.3, book.rating / 10.0 * 0.3)
    # View count bonus (0-0.2)
    if book.view_count and book.view_count > 0:
        base += min(0.2, min(1.0, book.view_count / 10000) * 0.2)
    return f"{max(0.4, min(1.0, base)):.2f}"

def get_prioritized_books(limit: int = 5000) -> list[dict]:
    """Return books sorted by computed priority for sitemap generation."""
    books = Book.objects.filter(is_published=True, is_deleted=False).order_by("-rating", "-view_count")[:limit]
    return [{"id": b.id, "slug": b.slug, "priority": compute_priority(b), "title": b.title} for b in books]
