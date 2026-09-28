"""sitemap.xml generator.

Generates a per-site sitemap.xml covering:
  - homepage
  - categories
  - books (with lastmod = book.updated_at)
  - chapters (with lastmod = chapter.updated_at)

Output: media/sitemaps/<host>.xml — served by Django or nginx.
"""

from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from django.conf import settings
from django.utils import timezone
from loguru import logger

from apps.novel.models import Book, Category, Chapter
from apps.sites.models import Site


SITEMAP_DIR = Path(settings.CRAWLER.get("DOWNLOAD_DIR", "")).parent / "sitemaps"
SITEMAP_DIR.mkdir(parents=True, exist_ok=True)


def _url_for(site: Site, path: str) -> str:
    base = f"https://{site.canonical_domain or site.host}/"
    return urljoin(base, path.lstrip("/"))


def _priority_book(book: Book) -> str:
    """Compute a priority 0.4-1.0 for a book based on its score."""
    p = 0.5 + (book.rating or 0) / 10.0
    return f"{max(0.4, min(1.0, p)):.2f}"


def _freq_for(book: Book) -> str:
    if book.status == Book.Status.ONGOING:
        return "daily"
    return "weekly"


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("'", "&apos;")
        .replace('"', "&quot;")
    )


def render_sitemap(site: Site, books: Iterable[Book]) -> str:
    """Render a sitemap XML for a site covering books + chapters."""
    urls = []

    # Home
    urls.append({
        "loc": _url_for(site, "/"),
        "lastmod": timezone.now().strftime("%Y-%m-%d"),
        "changefreq": "daily",
        "priority": "1.00",
    })

    # Categories
    for cat in Category.objects.filter(is_active=True, parent__isnull=True):
        urls.append({
            "loc": _url_for(site, f"/category/{cat.slug}"),
            "lastmod": timezone.now().strftime("%Y-%m-%d"),
            "changefreq": "weekly",
            "priority": "0.80",
        })

    # Books + their chapters — P1b fix: batch fetch chapters to avoid N+1
    books = list(books)
    book_ids = [b.id for b in books]
    # Batch fetch all chapters for these books in one query
    from apps.novel.models import Chapter
    all_chapters = Chapter.objects.filter(
        book_id__in=book_ids
    ).order_by("book_id", "order_index").values(
        "book_id", "order_index", "updated_at", "fetched_at"
    )
    # Group chapters by book_id
    chapters_by_book = {}
    for ch in all_chapters:
        bid = ch["book_id"]
        if bid not in chapters_by_book:
            chapters_by_book[bid] = []
        if len(chapters_by_book[bid]) < 200:  # cap at 200 per book
            chapters_by_book[bid].append(ch)
    
    for book in books:
        urls.append({
            "loc": _url_for(site, f"/book/{book.slug}"),
            "lastmod": (book.updated_at or timezone.now()).strftime("%Y-%m-%d"),
            "changefreq": _freq_for(book),
            "priority": _priority_book(book),
        })
        for ch in chapters_by_book.get(book.id, []):
            urls.append({
                "loc": _url_for(site, f"/book/{book.slug}/chapter/{ch['order_index']}"),
                "lastmod": (ch["updated_at"] or ch["fetched_at"] or timezone.now()).strftime("%Y-%m-%d"),
                "changefreq": "weekly",
                "priority": "0.60",
            })

    # Render XML
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{_esc(u['loc'])}</loc>")
        if u.get("lastmod"):
            lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        if u.get("changefreq"):
            lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        if u.get("priority"):
            lines.append(f"    <priority>{u['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines)


def generate_for_site(site: Site, *, limit_books: int = 5000) -> Path:
    """Generate sitemap.xml for one site, return the output path."""
    books = Book.objects.filter(is_published=True, is_deleted=False)[:limit_books]
    xml = render_sitemap(site, books)
    out = SITEMAP_DIR / f"{site.host}.xml"
    out.write_text(xml, encoding="utf-8")
    logger.info(f"[sitemap] {site.host} → {out} ({len(list(books))} books)")
    return out


def generate_for_all_sites() -> list[Path]:
    paths = []
    for site in Site.objects.filter(is_active=True):
        try:
            paths.append(generate_for_site(site))
        except Exception as e:
            logger.error(f"[sitemap] failed for {site.host}: {e!r}")
    return paths
