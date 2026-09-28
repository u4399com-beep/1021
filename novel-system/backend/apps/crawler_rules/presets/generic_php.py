"""通用 PHP 小说站规则模板 — 适用于大部分 PHP 小说站。

特征:
- URL 模式: /book.php?id= / /books/{id}.html / /novel/{id}/
- 内容容器: div#content / div.content / div#BookText / div#nr1
- 章节列表: ul li a / table tr td a / dl dd a
- 分页: a.next / a.pagelink / .page-next

突破策略:
1. 先用 httpx 试（很多 PHP 站没有反爬）
2. 403 → 切换 Playwright + Stealth
3. WAF → 使用 captcha solver
4. 编码: 优先 GBK/GB2312（很多老站用 GBK）
"""
from __future__ import annotations


LIST_CONFIG = {
    "item_selector": {
        "type": "css",
        "expr": "ul.book-list li, ul.list li, div.book-item, .novel-list-item, table.list tr[class], .grid li",
    },
    "book_url": {"type": "xpath", "expr": ".//a/@href"},
    "book_title": {"type": "css", "expr": "h3::text, h4::text, .title::text, .book-name::text, a::text, td.title a::text"},
    "book_author": {"type": "css", "expr": ".author::text, span.author::text, td.author::text, .book-author::text"},
    "book_cover": {"type": "xpath", "expr": ".//img/@src"},
    "book_intro": {"type": "css", "expr": ".intro::text, .summary::text, .book-intro::text"},
    "book_category": {"type": "css", "expr": ".cat::text, .category::text, span.cat::text"},
    "book_status": {"type": "css", "expr": ".status::text, .state::text, span.status::text"},
    "next_page": {"type": "css", "expr": "a.next::attr(href), a[rel=next]::attr(href), .pagelink a:last-child::attr(href)"},
}

BOOK_CONFIG = {
    "title": {"type": "css", "expr": "h1::text, h1.book-title::text, h1.title::text, .book-info h1::text"},
    "author": {"type": "css", "expr": ".author a::text, span.author::text, .book-info .author::text, #info p a::text, .book-author::text"},
    "cover": {"type": "xpath", "expr": "//div[contains(@class,'cover')]//img/@src | //div[@id='fmimg']//img/@src | //div[@class='book-cover']//img/@src"},
    "intro": {"type": "css", "expr": ".intro::text, .summary::text, #intro p::text, .book-intro p::text, .book-intro::text, .intro p::text"},
    "category": {"type": "css", "expr": ".category a::text, .cat a::text, .book-info .cat a::text, .book-category a::text", "multi": True},
    "keywords": {"type": "css", "expr": ".tags a::text, .keyword a::text, .book-tags a::text", "multi": True},
    "status": {"type": "regex", "expr": r"状态[:：]\s*(连载中|已完结|完结)"},
    "last_chapter_title": {"type": "css", "expr": ".last-chapter a::text, .newest a::text, .latest a::text"},
    "toc_url": {"type": "xpath", "expr": "//a[contains(text(),'目录') or contains(text(),'章节') or contains(@href,'chapter') or contains(@href,'mulu')]/@href"},
}

TOC_CONFIG = {
    "item_selector": {
        "type": "css",
        "expr": "ul.chapter-list li, .chapter-list a, .mulu li a, dl dd a, ul.list-chapter li a, .chapter-list li",
    },
    "volume_selector": {
        "type": "css",
        "expr": ".volume, .v-name, h2:contains('卷'), h3:contains('卷'), .book-volume",
    },
    "chapter_url": {"type": "xpath", "expr": ".//a/@href"},
    "chapter_title": {"type": "css", "expr": "a::text, span::text, .chapter-title::text"},
    "next_page": {"type": "css", "expr": "a.next::attr(href), a.pagelink[href*=next]::attr(href), .page-next::attr(href)"},
}

CHAPTER_CONFIG = {
    "title": {"type": "css", "expr": "h1.chapter-title::text, h1::text, .chapter-head h1::text, #title::text, .chapter-title::text"},
    "content": {"type": "css", "expr": "div.chapter-content, div.content, div#content, div#BookText, div#nr1, .read-content, .chapter-body, #nr1, .novel-content, div.bookContent"},
    "next_page": {"type": "css", "expr": "a.next::attr(href), a[href*=javascript]:contains('下一页')::attr(href), .page-next::attr(href)"},
    "remove_selectors": ["script", "iframe", "div.ad-container", "div.book-tag", "div.footer-banner"],
}

ANTI_DETECTION_HINTS = {
    "tier_required": "auto",  # 自动选择: 先 httpx, 失败切 playwright
    "cookie_required": False,
    "waf_captcha": False,
    "encoding": "auto",  # 自动检测 (GBK/GB2312/UTF-8)
    "note": (
        "通用 PHP 小说站模板。大部分 PHP 站无反爬，httpx 可直接抓取。\n"
        "如遇 403: 切换 Playwright + Stealth。\n"
        "如遇 WAF: 使用 captcha solver。\n"
        "编码: 很多老站用 GBK，encoding_handler 会自动检测。\n"
    ),
}
