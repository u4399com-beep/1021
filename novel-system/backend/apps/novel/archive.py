"""Data archiving (v44) — move old chapters to cold storage."""
import os, shutil, gzip, json
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from loguru import logger
from apps.novel.models import Chapter, Book


def archive_old_chapters(days: int = 365, dry_run: bool = False) -> dict:
    """Move chapter content older than N days to compressed archive files.

    - Chapter.content is gzipped and saved to media/archive/chapters/<book_id>/<ch_id>.txt.gz
    - Chapter.content is replaced with a placeholder pointing to the archive
    - Chapter.status set to 'archived'

    Returns: {archived_count, freed_bytes, errors}
    """
    archive_root = Path(settings.MEDIA_ROOT) / "archive" / "chapters"
    archive_root.mkdir(parents=True, exist_ok=True)
    cutoff = timezone.now() - timedelta(days=days)
    old_chapters = Chapter.objects.filter(
        updated_at__lt=cutoff,
        status__in=["published", "cleaned", "fetched"],
        content__isnull=False,
    ).exclude(content="")
    archived_count = 0
    freed_bytes = 0
    errors = []
    for ch in old_chapters.iterator():
        try:
            book_dir = archive_root / str(ch.book_id)
            book_dir.mkdir(exist_ok=True)
            archive_path = book_dir / f"{ch.id}.txt.gz"
            content_bytes = ch.content.encode("utf-8")
            with gzip.open(archive_path, "wb") as f:
                f.write(content_bytes)
            freed_bytes += len(content_bytes)
            ch.content = f"[archived to {archive_path}]"
            ch.status = "archived"
            ch.save(update_fields=["content", "status"])
            archived_count += 1
            if dry_run:
                logger.info(f"[dry-run] would archive chapter {ch.id}")
        except Exception as e:
            errors.append({"chapter_id": ch.id, "error": repr(e)})
    return {"archived_count": archived_count, "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / 1024 / 1024, 2), "errors": errors}
