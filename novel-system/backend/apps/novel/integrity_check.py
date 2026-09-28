"""Data integrity checker (v67) — verify foreign keys, indexes, constraints."""
from __future__ import annotations
from django.db import connection
from .models import Book, Chapter, Volume


def check_integrity() -> dict:
    """Run a full integrity check on the novel data.
    
    Returns: {ok: bool, issues: [...], stats: {...}}
    """
    issues = []
    
    # 1. Chapters without a book (orphaned)
    orphaned_chapters = Chapter.objects.filter(book__isnull=True).count()
    if orphaned_chapters:
        issues.append({"severity": "critical", "check": "orphaned_chapters", "count": orphaned_chapters})
    
    # 2. Chapters pointing to a soft-deleted book
    chapters_on_deleted = Chapter.objects.filter(book__is_deleted=True).count()
    if chapters_on_deleted:
        issues.append({"severity": "warning", "check": "chapters_on_deleted_book", "count": chapters_on_deleted})
    
    # 3. Volumes without chapters
    empty_volumes = Volume.objects.filter(chapters__isnull=True).count()
    if empty_volumes:
        issues.append({"severity": "info", "check": "empty_volumes", "count": empty_volumes})
    
    # 4. Books with chapter_count = 0 but have chapters
    for book in Book.objects.filter(is_deleted=False, chapter_count=0):
        actual = book.chapters.count()
        if actual > 0:
            issues.append({"severity": "warning", "check": "stale_chapter_count",
                          "book_id": book.id, "stored": 0, "actual": actual})
    
    # 5. Duplicate source_url within same book
    from django.db.models import Count
    dupes = Chapter.objects.values("book_id", "source_url").annotate(
        cnt=Count("id")
    ).filter(cnt__gt=1, source_url__isnull=False).exclude(source_url="")
    for d in dupes[:10]:
        issues.append({"severity": "warning", "check": "duplicate_source_url",
                      "book_id": d["book_id"], "url": d["source_url"], "count": d["cnt"]})
    
    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "issue_count": len(issues),
        "stats": {
            "total_books": Book.objects.filter(is_deleted=False).count(),
            "total_chapters": Chapter.objects.count(),
            "total_volumes": Volume.objects.count(),
        },
    }


def repair_stale_counts() -> dict:
    """Repair stale chapter_count / volume_count on books."""
    repaired = 0
    for book in Book.objects.filter(is_deleted=False):
        actual_ch = book.chapters.count()
        actual_vol = book.volumes.count()
        changed = False
        if book.chapter_count != actual_ch:
            book.chapter_count = actual_ch
            changed = True
        if book.volume_count != actual_vol:
            book.volume_count = actual_vol
            changed = True
        if changed:
            book.save(update_fields=["chapter_count", "volume_count"])
            repaired += 1
    return {"repaired": repaired}
