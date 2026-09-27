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


def build_epub(book, template: DownloadTemplate) -> Path:
    """生成 EPUB 文件 — 通过 ebooklib"""
    try:
        from ebooklib import epub
    except ImportError:
        # Fallback: produce txt
        return build_txt(book, template)

    out_dir = Path(settings.CRAWLER["DOWNLOAD_DIR"]) / str(book.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{book.title}.epub"

    ctx = {
        "site_name": book.source_site or "novel-system",
        "book_title": book.title,
        "book_author": book.author.name if book.author else "-",
        "book_intro": book.intro,
    }

    book_epub = epub.EpubBook()
    book_epub.set_title(book.title)
    book_epub.set_language("zh-CN")
    if book.author:
        book_epub.add_author(book.author.name)

    # Pre-frontmatter
    if template.book_preface:
        book_epub.add_item(epub.EpubHtml(title="前言", content=render_template_text(template.book_preface, ctx)))

    # Chapters
    chapters = list(book.chapters.filter(status="published").order_by("order_index"))
    toc = []
    for idx, ch in enumerate(chapters, start=1):
        content = ch.content or ""
        if template.enable_confusion:
            content = inject_confusion(content, template.confusion_density, template.confusion_chars)
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
    book_epub.spine = ["nav"] + toc

    style = "body{font-family:'Noto Serif SC',serif;line-height:1.8;}"
    book_epub.add_item(epub.EpubNavi)
    book_epub.add_item(epub.EpubItem(file_name="style.css", media_type="text/css", content=style))
    epub.write_epub(str(out_path), book_epub, {})
    return out_path


def build_download(book, template: DownloadTemplate, user=None) -> DownloadRecord:
    """主入口 — 根据模板生成文件并写入 DownloadRecord"""
    if template.output_format == "epub":
        path = build_epub(book, template)
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
