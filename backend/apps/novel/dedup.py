"""Book deduplication (v54) — detect duplicate books by title+author fingerprint."""
from __future__ import annotations
import hashlib
from django.db.models import Q
from .models import Book


def compute_fingerprint(title: str, author_name: str = "") -> str:
    """Compute a normalized fingerprint for a book.
    
    Normalization: lowercase, strip whitespace/punctuation, then SHA-256.
    """
    def norm(s):
        return ''.join(c.lower() for c in (s or "").strip() if c.isalnum())
    raw = f"{norm(title)}|{norm(author_name)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def find_duplicates(book: Book) -> list[dict]:
    """Find books that are likely duplicates of the given book."""
    fp = compute_fingerprint(book.title, book.author.name if book.author else "")
    # Exact fingerprint match
    candidates = Book.objects.filter(
        is_deleted=False
    ).exclude(id=book.id)
    duplicates = []
    for c in candidates:
        c_fp = compute_fingerprint(c.title, c.author.name if c.author else "")
        if c_fp == fp:
            duplicates.append({
                "book_id": c.id, "title": c.title, "author": c.author.name if c.author else "",
                "source_url": c.source_url, "match_type": "exact_fingerprint",
            })
    # Title-only fuzzy match (substring)
    if not duplicates:
        for c in candidates.filter(title__icontains=book.title[:6]):
            duplicates.append({
                "book_id": c.id, "title": c.title, "author": c.author.name if c.author else "",
                "source_url": c.source_url, "match_type": "title_substring",
            })
    return duplicates


def merge_duplicates(primary: Book, secondary_ids: list[int]) -> dict:
    """Merge secondary books into the primary book.
    
    Moves chapters from secondary books to primary, then soft-deletes secondaries.
    """
    from .models import Chapter
    moved = 0
    for sid in secondary_ids:
        try:
            sec = Book.objects.get(pk=sid)
            if sec.id == primary.id:
                continue
            # Move chapters
            for ch in sec.chapters.all():
                ch.book = primary
                ch.save(update_fields=["book"])
                moved += 1
            sec.is_deleted = True
            sec.save(update_fields=["is_deleted"])
        except Book.DoesNotExist:
            continue
    primary.chapter_count = primary.chapters.count()
    primary.save(update_fields=["chapter_count"])
    return {"merged": len(secondary_ids), "chapters_moved": moved, "primary_id": primary.id}
