"""文件下载引擎 — 拼装章节、插入混淆/广告/站点信息、输出 TXT 或 EPUB。"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.template import Context, Template

from .models import DownloadRecord, DownloadTemplate


def render_template_text(text: str, context: dict) -> str:
    if not text or "{" not in text:
        return text
    try:
        return Template(text).render(Context(context))
    except Exception:
        return text


def inject_confusion(text: str, density: float, charset: str) -> str:
    """在每个段落尾部插入零宽字符。"""
    if not text or density <= 0 or not charset:
        return text
    out_chars = []
    for ch in text:
        out_chars.append(ch)
        if ch == "\n":
            if random.random() < density:
                out_chars.append(random.choice(list(charset)))
    return "".join(out_chars)


def build_txt(book, template: DownloadTemplate) -> Path:
    """生成 TXT 文件"""
    out_dir = Path(settings.CRAWLER["DOWNLOAD_DIR"]) / str(book.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book.title}.txt"

    ctx = {
        "site_name": book.source_site or "novel-system",
        "book_title": book.title,
        "book_author": book.author.name if book.author else "-",
        "book_intro": book.intro,
    }

    with out_path.open("w", encoding="utf-8") as fp:
        if template.book_preface:
            fp.write(render_template_text(template.book_preface, ctx))
            fp.write("\n\n")
        if template.site_info_block:
            fp.write(render_template_text(template.site_info_block, ctx))
            fp.write("\n\n")

        for ch in book.chapters.filter(status="published").order_by("order_index"):
            fp.write("\n\n" + "=" * 50 + "\n")
            if template.chapter_header:
                fp.write(render_template_text(template.chapter_header, ctx))
                fp.write("\n")
            fp.write(ch.title + "\n\n")
            content = ch.content or ""
            if template.enable_confusion:
                content = inject_confusion(content, template.confusion_density, template.confusion_chars)
            fp.write(content)
            fp.write("\n")
            if template.chapter_footer:
                fp.write(render_template_text(template.chapter_footer, ctx))
                fp.write("\n")
            if template.ad_block and random.random() < 0.3:
                fp.write(render_template_text(template.ad_block, ctx))
                fp.write("\n")

        if template.book_afterword:
            fp.write("\n\n")
            fp.write(render_template_text(template.book_afterword, ctx))

    return out_path


def build_epub(book, template: DownloadTemplate, site=None) -> Path:
    """生成 EPUB 文件 — 通过 ebooklib，并嵌入封面图 + 水印"""
    try:
        from ebooklib import epub
    except ImportError:
        # Fallback: produce txt
        return build_txt(book, template)

    out_dir = Path(settings.CRAWLER["DOWNLOAD_DIR"]) / str(book.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book.title}.epub"

    ctx = {
        "site_name": (site.name if site else (book.source_site or "novel-system")),
        "book_title": book.title,
        "book_author": book.author.name if book.author else "-",
        "book_intro": book.intro,
    }

    book_epub = epub.EpubBook()
    book_epub.set_title(book.title)
    book_epub.set_language("zh-CN")
    book_epub.set_identifier(f"novel-system-{book.id}")
    if book.author:
        book_epub.add_author(book.author.name)
    # Extended metadata (DC terms supported by ebooklib)
    if book.author and book.author.intro:
        book_epub.add_metadata("DC", "contributor", book.author.intro[:200])
    if book.intro:
        book_epub.add_metadata("DC", "description", book.intro[:500])
    if book.source_site:
        book_epub.add_metadata("DC", "source", book.source_site)
    if book.source_url:
        book_epub.add_metadata("DC", "relation", book.source_url)
    # Rights + publisher (default to site name)
    publisher = (site.name if site else "novel-system")
    book_epub.add_metadata("DC", "publisher", publisher)
    book_epub.add_metadata("DC", "rights", f"All rights reserved by {publisher}")
    if book.categories.first():
        book_epub.add_metadata("DC", "subject", book.categories.first().name)
    # Publication date
    from datetime import datetime
    pub_date = book.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(book, 'created_at') and book.created_at else datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    book_epub.add_metadata("DC", "date", pub_date)

    # ─── 封面嵌入 ─────────────────────────────────────────────
    cover_path = _resolve_cover_image(book)
    cover_xhtml = None
    if cover_path:
        with open(cover_path, "rb") as f:
            cover_bytes = f.read()
        cover_filename = "cover.webp" if str(cover_path).endswith(".webp") else "cover.jpg"
        cover_mime = "image/webp" if cover_filename.endswith(".webp") else "image/jpeg"
        try:
            book_epub.set_cover("cover.jpg", cover_bytes)
        except Exception:
            img_item = epub.EpubItem(
                uid="cover-image",
                file_name=f"images/{cover_filename}",
                media_type=cover_mime,
                content=cover_bytes,
            )
            book_epub.add_item(img_item)

        # Optional cover XHTML page (some readers prefer)
        try:
            cover_xhtml = epub.EpubCoverHtml(file_name="cover.xhtml")
            cover_xhtml.content = (
                '<html xmlns="http://www.w3.org/1999/xhtml">'
                '<head><title>Cover</title></head>'
                f'<body><img src="images/{cover_filename}" alt="cover" '
                'style="width:100%;height:auto;"/></body></html>'
            )
            book_epub.add_item(cover_xhtml)
        except Exception:
            pass

    # ─── 水印嵌入 ─────────────────────────────────────────────
    watermark_svg = _build_watermark_svg(site, book)
    if watermark_svg:
        try:
            wm_item = epub.EpubItem(
                uid="watermark",
                file_name="images/watermark.svg",
                media_type="image/svg+xml",
                content=watermark_svg.encode("utf-8"),
            )
            book_epub.add_item(wm_item)
            # Inject watermark CSS that overlays it on every chapter page
            style += (
                ".watermark-layer {"
                "position: fixed;"
                "top: 50%; left: 50%;"
                "transform: translate(-50%, -50%);"
                "width: 60%; opacity: 0.05;"
                "pointer-events: none; z-index: -1;"
                "}"
            )
            # Also add a hidden watermark metadata
            book_epub.add_metadata(
                None, "watermark",
                f"{site.name if site else 'novel-system'}-{book.id}-{book.slug}",
            )
        except Exception:
            pass

    # Pre-frontmatter
    if template.book_preface:
        book_epub.add_item(epub.EpubHtml(title="前言", content=render_template_text(template.book_preface, ctx)))

    # Chapters
    chapters = list(book.chapters.filter(status="published").order_by("order_index"))
    toc = []
    watermark_html = (
        '<div class="watermark-layer">'
        '<img src="images/watermark.svg" alt="" />'
        '</div>'
    ) if watermark_svg else ''
    for idx, ch in enumerate(chapters, start=1):
        content = ch.content or ""
        if template.enable_confusion:
            content = inject_confusion(content, template.confusion_density, template.confusion_chars)
        # Prepend watermark layer
        if watermark_html:
            content = watermark_html + content
        html = f"<h2>{ch.title}</h2>" + content
        if template.chapter_header:
            html = render_template_text(template.chapter_header, ctx) + html
        if template.chapter_footer:
            html = html + render_template_text(template.chapter_footer, ctx)
        c = epub.EpubHtml(title=ch.title, file_name=f"ch{idx:05d}.xhtml")
        c.set_content(html)
        book_epub.add_item(c)
        toc.append(c)
    book_epub.toc = toc

    # spine — put cover first if available, then nav, then chapters
    if cover_xhtml:
        book_epub.spine = [cover_xhtml, "nav"] + toc
    else:
        book_epub.spine = ["nav"] + toc

    style = "body{font-family:'Noto Serif SC',serif;line-height:1.8;}"
    book_epub.add_item(epub.EpubNavi())
    book_epub.add_item(epub.EpubItem(file_name="style.css", media_type="text/css", content=style))
    epub.write_epub(str(out_path), book_epub, {})
    return out_path


def _resolve_cover_image(book) -> Path | None:
    """Return a local Path to the book cover image, or None.

    Priority:
      1. book.cover (ImageField) — if uploaded locally
      2. book.cover_url — downloaded to a cache (reused if exists)
    """
    if book.cover:
        try:
            p = Path(book.cover.path)
            if p.exists():
                return p
        except Exception:
            pass

    if not book.cover_url:
        return None

    import httpx
    import os
    from urllib.parse import urlparse

    cache_dir = Path(settings.CRAWLER["COVER_DIR"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(urlparse(book.cover_url).path)[1] or ".jpg"
    if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    cache_path = cache_dir / f"book_{book.id}{ext.lower()}"
    if cache_path.exists():
        return cache_path

    try:
        with httpx.Client(timeout=30, follow_redirects=True) as cli:
            r = cli.get(book.cover_url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return None
            cache_path.write_bytes(r.content)
            return cache_path
    except Exception as e:
        print(f"[epub cover download failed] {e!r}")
        return None


def _build_watermark_svg(site, book) -> str | None:
    """Build a transparent SVG watermark embedded into the EPUB.

    The watermark is invisible to the reader (opacity 0.05) but contains
    an encoded identifier that can be used to trace the source of leaked
    copies back to the originating site / book / download date.

    Returns: SVG string, or None on error.
    """
    import hashlib
    import time

    try:
        site_name = site.name if site else (book.source_site or "novel-system")
        site_host = site.host if site else "novel-system"
        # Composite identifier: site-host + book-id + slug + timestamp
        ts = int(time.time())
        identifier = f"{site_host}|{book.id}|{book.slug}|{ts}"
        # Hash the identifier for compactness
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:16].upper()

        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">
  <text x="400" y="200" text-anchor="middle"
        font-family="sans-serif" font-size="28"
        fill="#000000" opacity="0.05"
        transform="rotate(-30 400 200)">
    {site_name} · {digest}
  </text>
</svg>"""
        return svg
    except Exception as e:
        print(f"[watermark build failed] {e!r}")
        return None


def build_download(book, template: DownloadTemplate, user=None, site=None) -> DownloadRecord:
    """主入口 — 根据模板生成文件并写入 DownloadRecord"""
    if template.output_format == "epub":
        path = build_epub(book, template, site=site)
    else:
        path = build_txt(book, template)

    record = DownloadRecord.objects.create(
        template=template,
        book=book,
        output_format=template.output_format,
        file_path=str(path),
        file_size=path.stat().st_size,
        chapters_count=book.chapters.filter(status="published").count(),
        created_by=user,
    )
    return record
