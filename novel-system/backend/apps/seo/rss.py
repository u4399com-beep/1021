"""RSS / Atom feeds.

Generates per-site RSS XML for:
  - latest books
  - latest chapters of a specific book

Output format: RSS 2.0 (works in all readers), with Atom 1.0 link for compatibility.
"""
from __future__ import annotations

from typing import Iterable
from urllib.parse import urljoin

from django.utils import timezone
from django.utils.html import escape

from apps.novel.models import Book, Chapter
from apps.sites.models import Site


def _url_for(site: Site, path: str) -> str:
    base = f"https://{site.canonical_domain or site.host}/"
    return urljoin(base, path.lstrip("/"))


def _esc(text: str) -> str:
    return escape(str(text or ""))


def render_site_rss(site: Site, books: Iterable[Book], *, limit: int = 50) -> str:
    """Render site-level RSS 2.0 of latest books."""
    pub_date = timezone.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    base = _url_for(site, "/")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    lines.append("  <channel>")
    lines.append(f"    <title>{_esc(site.name)} - 最新小说</title>")
    lines.append(f"    <link>{_esc(base)}</link>")
    lines.append(f"    <description>{_esc(site.site_description or site.name)}</description>")
    lines.append(f"    <language>{_esc(site.geo_lang or 'zh-CN')}</language>")
    lines.append(f"    <lastBuildDate>{pub_date}</lastBuildDate>")
    lines.append(f"    <atom:link href=\"{_esc(_url_for(site, '/rss.xml'))}\" rel=\"self\" type=\"application/rss+xml\"/>")

    for book in list(books)[:limit]:
        book_url = _url_for(site, f"/book/{book.slug}")
        item_date = (book.updated_at or book.created_at).strftime("%a, %d %b %Y %H:%M:%S +0800")
        lines.append("    <item>")
        lines.append(f"      <title>{_esc(book.title)}</title>")
        lines.append(f"      <link>{_esc(book_url)}</link>")
        lines.append(f"      <guid isPermaLink=\"true\">{_esc(book_url)}</guid>")
        lines.append(f"      <description>{_esc(book.intro or '')[:500]}</description>")
        if book.author:
            lines.append(f"      <author>{_esc(book.author.name)}</author>")
        for c in book.categories.all()[:5]:
            lines.append(f"      <category>{_esc(c.name)}</category>")
        lines.append(f"      <pubDate>{item_date}</pubDate>")
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines)


def render_book_chapter_rss(site: Site, book: Book, *, limit: int = 50) -> str:
    """Per-book RSS of latest chapters."""
    pub_date = timezone.now().strftime("%a, %d %b %Y %H:%M:%S +0800")
    base = _url_for(site, "/")
    book_url = _url_for(site, f"/book/{book.slug}")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    lines.append("  <channel>")
    lines.append(f"    <title>{_esc(book.title)} - 最新章节</title>")
    lines.append(f"    <link>{_esc(book_url)}</link>")
    lines.append(f"    <description>{_esc(book.intro or '')}</description>")
    lines.append(f"    <language>{_esc(site.geo_lang or 'zh-CN')}</language>")
    lines.append(f"    <lastBuildDate>{pub_date}</lastBuildDate>")
    lines.append(f"    <atom:link href=\"{_esc(_url_for(site, f'/book/{book.slug}/rss.xml'))}\" rel=\"self\" type=\"application/rss+xml\"/>")

    chapters = book.chapters.all().order_by("-order_index")[:limit]
    for ch in chapters:
        ch_url = _url_for(site, f"/book/{book.slug}/chapter/{ch.order_index}")
        item_date = (ch.fetched_at or ch.updated_at or ch.created_at).strftime("%a, %d %b %Y %H:%M:%S +0800")
        lines.append("    <item>")
        lines.append(f"      <title>{_esc(ch.title)}</title>")
        lines.append(f"      <link>{_esc(ch_url)}</link>")
        lines.append(f"      <guid isPermaLink=\"true\">{_esc(ch_url)}</guid>")
        lines.append(f"      <description>第 {ch.order_index} 章 — 字数 {ch.word_count}</description>")
        lines.append(f"      <pubDate>{item_date}</pubDate>")
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines)
