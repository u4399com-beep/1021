"""Full crawler pipeline — orchestrates fetch + parse + clean + classify + store.

This is what `apps/crawler_tasks/tasks.crawl_one_url` calls.
"""
from __future__ import annotations

import os
import random
import time
from typing import Any
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.db.models import Sum as models_Sum
from django.utils import timezone
from loguru import logger

from apps.content_cleaner.engine import clean_content
from apps.novel.models import Author, Book, Category, Chapter, Tag
from apps.smart_classifier.engine import classify_book, detect_finished

from .fetcher import fetch_page
from .parsers.factory import build_parser


def crawl_book_pipeline(task, url: str) -> tuple[Book | None, list[Chapter]]:
    """Top-level pipeline — single book URL.

    Steps:
      1. Fetch book info page → parse → upsert Book
      2. Fetch TOC page (optional paged) → parse → list of (title, url)
      3. Shuffle order (if enabled) → dedup (if enabled)
      4. For each chapter URL: fetch + parse + clean + store
      5. Smart-classify book + detect finished status
      6. Download cover image (if enabled)
    """
    book_rule = task.book_rule
    toc_rule = task.toc_rule
    chapter_rule = task.chapter_rule

    if not book_rule:
        logger.warning(f"task {task.id} missing book rule, skip")
        return None, []

    # 1. Fetch + parse book info
    html = fetch_page(url)
    book_parser = build_parser(book_rule.config)
    book_data = book_parser.parse("book", html, base_url=url)
    book = _upsert_book(book_data, source_url=url)
    if not book:
        logger.error(f"failed to upsert book from {url}")
        return None, []

    # 2. Fetch TOC
    toc_url = book_data.get("toc_url") or url
    if toc_rule:
        toc_html = fetch_page(toc_url)
        toc_parser = build_parser(toc_rule.config)
        toc_data = toc_parser.parse("toc", toc_html, base_url=toc_url)
        chapters = toc_data.get("chapters", [])
        # Follow pagination if configured
        if "next_page" in toc_rule.config and toc_data.get("next_page"):
            _ = toc_data["next_page"]  # would recurse — left as TODO for next iteration
    else:
        chapters = []

    # 3. Disorder + dedup
    if task.enable_disorder:
        chapters = _disorder(chapters)
    if task.enable_dedup_by_url:
        chapters = _dedup_by_url(chapters, book)
    if task.enable_dedup_by_title:
        chapters = _dedup_by_title(chapters, book)

    # 4. Fetch each chapter
    saved_chapters = []
    if chapter_rule and chapters:
        for idx, ch_meta in enumerate(chapters, start=1):
            ch_url = ch_meta.get("url", "")
            ch_title = ch_meta.get("title", "")
            vol_name = ch_meta.get("volume") or None
            if not ch_url:
                continue
            chapter = _crawl_chapter(task, book, ch_url, ch_title, idx, chapter_rule, volume_name=vol_name)
            if chapter:
                saved_chapters.append(chapter)
            # honor pause/stop
            task.refresh_from_db()
            if task.status in ("paused", "stopped"):
                break
            # random interval
            time.sleep(random.uniform(task.interval_min, task.interval_max))

    # 5. Smart classify + finished detection
    if task.enable_classifier:
        cats = classify_book(book.title, book.intro or "")
        if cats:
            for c in cats[:3]:
                obj, _ = Category.objects.get_or_create(name=c["name"], defaults={"slug": c["name"]})
                book.categories.add(obj)
    if task.enable_finished_detection:
        if detect_finished(book.title, book.intro or "", book.last_chapter_title or ""):
            book.status = Book.Status.COMPLETED
            book.finished_at = timezone.now()

    # 6. Update stats + cover
    book.chapter_count = book.chapters.count()  # COUNT query — efficient
    from django.db.models import Sum
    book.word_count = book.chapters.aggregate(total=Sum("word_count"))["total"] or 0
    book.volume_count = book.volumes.count()
    if book.last_chapter_title:
        # take last chapter by order
        last = book.chapters.order_by("-order_index").first()
        if last:
            book.last_chapter_title = last.title
    book.save()
    if task.download_cover and book_data.get("cover"):
        _download_cover(book, book_data["cover"])

    return book, saved_chapters


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _upsert_book(book_data: dict, *, source_url: str) -> Book | None:
    if not book_data or not book_data.get("title"):
        return None
    _t = str(book_data["title"]).strip()
    if not _t or len(_t) > 500:
        return None

    # v181: validate book data quality
    from .quality_validator import validate_book_data
    qv = validate_book_data(book_data)
    if not qv["valid"]:
        logger.warning(f"book data quality issues: {qv["issues"]}")
    title = str(book_data["title"]).strip()
    author_name = (book_data.get("author") or "").strip() or "佚名"
    author, _ = Author.objects.get_or_create(name=author_name)

    book, created = Book.objects.update_or_create(
        source_url=source_url,
        defaults={
            "title": title,
            "author": author,
            "intro": (book_data.get("intro") or "")[:5000],
            "cover_url": book_data.get("cover") or "",
            "last_chapter_title": book_data.get("last_chapter_title") or "",
            "source_site": urlparse(source_url).netloc,
        },
    )

    # status
    status_raw = book_data.get("status") or ""
    if status_raw and ("完结" in status_raw):
        book.status = Book.Status.COMPLETED
    elif status_raw and "连载" in status_raw:
        book.status = Book.Status.ONGOING

    # keywords as tags
    kws = book_data.get("keywords") or []
    if isinstance(kws, str):
        kws = [kws]
    book.keywords = list(kws)
    book.save()

    # categories (raw strings)
    cats = book_data.get("category") or []
    if isinstance(cats, str):
        cats = [cats]
    for c in cats:
        cat_obj, _ = Category.objects.get_or_create(name=c, defaults={"slug": c})
        book.categories.add(cat_obj)
    return book


def _disorder(chapters: list[dict]) -> list[dict]:
    """Shuffle chapter order — preserves a hidden original order in DB column.

    Volumes are respected: chapters within the same volume are shuffled
    only among themselves; they never cross volume boundaries. The `volume`
    key (if present in the chapter dict) is used to group them.
    """
    if not chapters:
        return chapters

    # Group chapters by volume key (None / 0 / "" => "default" group)
    grouped: dict[str, list[dict]] = {}
    for ch in chapters:
        vol_key = str(ch.get("volume") or ch.get("volume_id") or "default")
        grouped.setdefault(vol_key, []).append(ch)

    # Shuffle each group independently, then concatenate in original volume order
    out: list[dict] = []
    # Preserve insertion order of volumes (Python 3.7+ dict)
    for vol_key, group_chapters in grouped.items():
        shuffled = list(group_chapters)
        random.shuffle(shuffled)
        out.extend(shuffled)
    return out


def _check_disorder(book: Book) -> dict:
    """Verify the disorder reordering is correctly applied.

    Returns:
        {
          "has_disorder": bool,        # whether any chapter has disorder_applied=True
          "violates_volume_boundary": bool,  # if a chapter appears outside its volume
          "total_chapters": int,
          "volumes_count": int,
          "by_volume": {vol_name: {total, disorder_count, ordered_correctly}},
        }
    """
    result = {
        "has_disorder": False,
        "violates_volume_boundary": False,
        "total_chapters": 0,
        "volumes_count": 0,
        "by_volume": {},
    }

    chapters = list(book.chapters.all().order_by("order_index"))
    result["total_chapters"] = len(chapters)
    result["volumes_count"] = book.volumes.count()

    # Group chapters by volume, in order_index order
    by_vol: dict[int | None, list[Chapter]] = {}
    for ch in chapters:
        by_vol.setdefault(ch.volume_id, []).append(ch)

    # Check each volume's chapters form a contiguous block in the book's ordered list
    sorted_chapters = chapters
    contiguous_check_ok = True
    seen_volumes = set()
    last_volume_id = None
    for ch in sorted_chapters:
        if ch.volume_id != last_volume_id:
            if ch.volume_id in seen_volumes:
                contiguous_check_ok = False
            seen_volumes.add(ch.volume_id)
            last_volume_id = ch.volume_id
    result["violates_volume_boundary"] = not contiguous_check_ok

    # Per-volume summary
    for vol_id, vol_chapters in by_vol.items():
        vol = book.volumes.filter(id=vol_id).first() if vol_id else None
        result["by_volume"][vol.name if vol else "未分卷"] = {
            "total": len(vol_chapters),
            "disorder_count": sum(1 for c in vol_chapters if c.disorder_applied),
            "ordered_correctly": all(
                c.order_index == idx + 1 for idx, c in enumerate(
                    sorted(vol_chapters, key=lambda x: x.order_index)
                )
            ),
        }
        if any(c.disorder_applied for c in vol_chapters):
            result["has_disorder"] = True

    return result


def _dedup_by_url(chapters: list[dict], book: Book) -> list[dict]:
    existing = set(book.chapters.values_list("source_url", flat=True))
    seen = set()
    out = []
    for ch in chapters:
        url = ch.get("url", "")
        if url in existing or url in seen:
            continue
        seen.add(url)
        out.append(ch)
    return out


def _dedup_by_title(chapters: list[dict], book: Book) -> list[dict]:
    existing = set(book.chapters.values_list("title", flat=True))
    seen = set()
    out = []
    for ch in chapters:
        title = ch.get("title", "")
        if title in existing or title in seen:
            continue
        seen.add(title)
        out.append(ch)
    return out


def _crawl_chapter(task, book, url, title, idx, rule, volume_name: str | None = None) -> Chapter | None:
    """Fetch + parse + clean a single chapter.

    Follows chapter-content pagination via `next_page` selector if present
    in the rule config. Pages are concatenated in order with separator.

    Args:
        volume_name: if provided, link the chapter to a Volume with this name
                     (creating it if it doesn't exist).
    """
    try:
        # Fetch all pages of this chapter (some novels split chapters across pages)
        pages_content = []
        pages_titles = []
        current_url = url
        seen_urls = set()
        max_pages = 20  # safety cap
        for _page_idx in range(max_pages):
            if current_url in seen_urls:
                break
            seen_urls.add(current_url)

            html = fetch_page(current_url)
            parser = build_parser(rule.config)
            data = parser.parse("chapter", html, base_url=current_url)
            page_content = data.get("content") or ""
            if isinstance(page_content, bytes):
                page_content = page_content.decode("utf-8", errors="replace")
            if page_content:
                pages_content.append(page_content)
            page_title = data.get("title") or ""
            if page_title and page_title not in pages_titles:
                pages_titles.append(page_title)

            # Follow next_page if configured
            next_spec_dict = rule.config.get("next_page")
            if not next_spec_dict:
                break
            next_url = _resolve_next_page(current_url, html, next_spec_dict)
            if not next_url or next_url == current_url:
                break
            current_url = next_url

        # Combine all pages
        content = "\n\n".join(pages_content)
        # If title has multiple page versions, pick the first
        final_title = title or (pages_titles[0] if pages_titles else "未命名")

        if task.enable_cleaner:
            content = clean_content(content, target="chapter")
        word_count = len(content)

        storage = task.content_storage
        txt_path = ""
        if storage in ("txt", "both"):
            try:
                ch_dir = os.path.join(settings.CRAWLER["CHAPTER_DIR"], str(book.id))
                os.makedirs(ch_dir, exist_ok=True)
                fn = f"{idx:05d}_{(final_title or 'untitled')[:30]}.txt"
                with open(os.path.join(ch_dir, fn), "w", encoding="utf-8") as f:
                    f.write(content)
                txt_path = os.path.join(ch_dir, fn)
            except Exception as e:
                logger.warning(f"chapter txt write failed: {e!r}")

        # Resolve volume FK if volume_name is given
        volume_obj = None
        if volume_name:
            from apps.novel.models import Volume
            vol_idx = book.volumes.count() + 1
            volume_obj, _ = Volume.objects.get_or_create(
                book=book, name=volume_name,
                defaults={"order_index": vol_idx},
            )

        # v181: validate chapter quality
        from .quality_validator import validate_chapter_data
        cv = validate_chapter_data({"title": final_title, "content": content})
        if not cv["valid"]:
            logger.warning(f"chapter quality issues: {cv["issues"]}")
        chapter, _ = Chapter.objects.update_or_create(
            book=book, source_url=url,
            defaults={
                "title": final_title,
                "order_index": idx,
                "source_order": idx,
                "disorder_applied": task.enable_disorder,
                "volume": volume_obj,
                "content": content if storage in ("db", "both") else "",
                "txt_path": txt_path,
                "word_count": word_count,
                "source_paged": len(pages_content) > 1,
                "source_page_count": len(pages_content),
                "status": "cleaned" if task.enable_cleaner else "fetched",
                "fetched_at": timezone.now(),
            },
        )
        return chapter
    except Exception as e:
        logger.error(f"chapter fetch failed url={url} err={e!r}")
        return None


def _resolve_next_page(current_url: str, html: str, next_spec_dict: dict) -> str | None:
    """Extract and absolutize the next-page URL from chapter HTML."""
    try:
        from .parsers.selectors import SelectorSpec, apply, _parse_html
        spec = SelectorSpec.from_dict(next_spec_dict)
        spec.base_url = current_url
        tree = _parse_html(html)
        next_url = apply(spec, tree)
        if next_url and isinstance(next_url, str):
            return next_url
        return None
    except Exception:
        return None


def _download_cover(book: Book, cover_url: str):
    if not cover_url:
        return
    try:
        from io import BytesIO

        import httpx
        from PIL import Image

        with httpx.Client(timeout=30, follow_redirects=True) as cli:
            r = cli.get(cover_url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return
            img = Image.open(BytesIO(r.content)).convert("RGB")
            out_dir = settings.CRAWLER["COVER_DIR"]
            os.makedirs(out_dir, exist_ok=True)
            fname = f"book_{book.id}.webp"
            out_path = os.path.join(out_dir, fname)
            img.save(out_path, format="WEBP", quality=settings.CRAWLER["COVER_QUALITY"])
            book.cover.name = f"uploads/covers/{fname}"
            book.save(update_fields=["cover"])
    except Exception as e:
        logger.warning(f"cover download failed: {e!r}")
