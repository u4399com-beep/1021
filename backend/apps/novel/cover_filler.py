"""Cover filler (v47) — generate placeholder cover for books without one."""
from __future__ import annotations
from pathlib import Path
from django.conf import settings
from PIL import Image, ImageDraw, ImageFont
from loguru import logger
from apps.novel.models import Book


def generate_placeholder_cover(book: Book) -> Path:
    """Generate a simple placeholder cover image with the book title."""
    cover_dir = Path(settings.CRAWLER["COVER_DIR"])
    cover_dir.mkdir(parents=True, exist_ok=True)
    out_path = cover_dir / f"placeholder_{book.id}.webp"
    # Create 300x400 image with light blue background
    img = Image.new("RGB", (300, 400), color=(230, 247, 255))
    draw = ImageDraw.Draw(img)
    # Draw title text (basic, no font → uses default)
    title = book.title[:8]  # truncate
    draw.text((50, 180), title, fill=(30, 136, 229))
    draw.text((50, 220), f"ID: {book.id}", fill=(120, 144, 156))
    img.save(out_path, format="WEBP", quality=85)
    book.cover.name = f"uploads/covers/placeholder_{book.id}.webp"
    book.save(update_fields=["cover"])
    return out_path


def fill_missing_covers(limit: int = 100) -> dict:
    """Find books without covers and generate placeholders."""
    books = Book.objects.filter(cover__isnull=True, cover_url="", is_deleted=False)[:limit]
    filled = 0
    for book in books:
        try:
            generate_placeholder_cover(book)
            filled += 1
        except Exception as e:
            logger.warning(f"placeholder cover failed for book {book.id}: {e!r}")
    return {"filled": filled, "checked": books.count()}
