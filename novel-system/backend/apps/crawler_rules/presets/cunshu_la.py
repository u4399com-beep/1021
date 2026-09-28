"""cunshu.la 采集规则集

cunshu.la 是一个国内小说站，使用了 GoEdge WAF 验证码保护。
直接 httpx / Firecrawl 抓取会返回 403，需要走 Browser Use 或 Playwright+Stealth
通过验证码（半自动 / cookie 复用）。

本文件提供 4 套规则的 JSON 配置（正则 + CSS + XPath 混合使用），
以及导入命令 `seed_cunshu_la_rules` 用于一键初始化。

URL 模式（推断自常见 PHP 小说站结构，需根据实际抓取页面调整）：
  - 列表页:  https://www.cunshu.la/library.php?sort=latest&page={page}
  - 书籍页:  https://www.cunshu.la/book.php?id={id}   或  /books/{id}.html
  - 章节目录: https://www.cunshu.la/book.php?id={id}  或  /chapter.php?bid={id}
  - 章节内容: https://www.cunshu.la/read.php?bid={id}&cid={cid}  或 /chapter/{bid}/{cid}.html

测试方法：
  1. 后台 → 采集规则 → 新建 → 选 cunshu.la 源
  2. 把下面的 list / book / toc / chapter 配置 JSON 粘到对应规则的 config 字段
  3. 测试时使用 Playwright tier（系统设置 → 采集引擎 → 选 playwright）
  4. 在测试 URL 中填入列表页 URL，可手动验证解析器
"""


LIST_CONFIG = {
    "url_pattern": "https://www.cunshu.la/library.php?sort=latest&page={page}",
    "pagination": {
        "enabled": True,
        "template": "https://www.cunshu.la/library.php?sort=latest&page={page}",
        "var": "page",
        "start": 1,
        "end": 100,
        "step": 1,
    },
    "item_selector": {
        "type": "css",
        "expr": "ul.library-list li, div.book-item, .novel-list-item, .book-list-item, ul.book-list li, table.list tr[class]",
    },
    "book_url":     {
        "type": "xpath",
        "expr": ".//a[contains(@href,'book') or contains(@href,'/b/')]/@href",
        "template": "https://www.cunshu.la{0}"
    },
    "book_title":   {"type": "css", "expr": "h3.title::text, h4 a::text, .book-name::text, td.title a::text"},
    "book_author":  {"type": "css", "expr": ".author::text, span.author::text, td.author::text"},
    "book_cover":   {"type": "xpath", "expr": ".//img/@src"},
    "book_intro":   {"type": "css", "expr": ".intro::text, .summary::text"},
    "book_category": {"type": "css", "expr": ".category::text, .cat::text"},
    "book_status":  {"type": "css", "expr": ".status::text, .state::text"},
    "next_page":    {"type": "css", "expr": "a.next::attr(href), a[rel=next]::attr(href)"},
}


BOOK_CONFIG = {
    "title":   {"type": "css", "expr": "h1.book-title::text, h1.title::text, .book-info h1::text, #info h1::text, h1::text, .bookname h1::text"},
    "author":  {"type": "css", "expr": ".author a::text, span.author::text, .book-info .author::text, #info p a::text"},
    "cover":   {"type": "xpath", "expr": "//div[contains(@class,'cover')]//img/@src | //div[@id='fmimg']//img/@src"},
    "intro":   {"type": "css", "expr": ".intro::text, .summary::text, #intro p::text, .book-intro p::text", "multi": False},
    "category": {"type": "css", "expr": ".category a::text, .cat a::text, .book-info .cat a::text", "multi": True},
    "keywords": {"type": "css", "expr": ".tags a::text, .keyword a::text", "multi": True},
    "status":  {"type": "regex", "expr": r"状态[:：]\s*(连载中|已完结|完结)"},
    "last_chapter_title": {"type": "css", "expr": ".last-chapter a::text, .newest a::text"},
    "toc_url": {"type": "xpath", "expr": "//a[contains(text(),'章节目录') or contains(@class,'chapter-list') or contains(@href,'chapter')]/@href"},
}


TOC_CONFIG = {
    "item_selector": {
        "type": "css",
        "expr": "ul.chapter-list li, div.chapter-list a, .mulu li a, dd a",
    },
    "volume_selector": {
        "type": "css",
        "expr": ".volume, .v-name, h2:contains('卷'), h3:contains('卷')",
    },
    "chapter_url":   {"type": "xpath", "expr": ".//a/@href"},
    "chapter_title": {"type": "css", "expr": "a::text, span::text"},
    "next_page":     {"type": "css", "expr": "a.next::attr(href), a.pagelink[href*=next]::attr(href)"},
}


CHAPTER_CONFIG = {
    "title":   {"type": "css", "expr": "h1.chapter-title::text, h1::text, .chapter-head h1::text, #title::text"},
    "content": {"type": "css", "expr": "div.chapter-content, div.content, div#content, div#BookText, div#nr1, .read-content, .chapter-body, #nr1, .novel-content"},
    "next_page": {"type": "css", "expr": "a.next::attr(href), a[href*=javascript]:contains('下一页')::attr(href)"},
    "remove_selectors": [
        "script",
        "iframe",
        "div.ad-container",
        "div.book-tag",
        "div.footer-banner",
    ],
}


ANTI_DETECTION_HINTS = {
    "tier_required": "playwright",
    "cookie_required": True,
    "waf_captcha": True,
    "note": (
        "cunshu.la 使用 GoEdge WAF，首次访问会触发验证码。建议：\n"
        "1. 在系统设置 → 采集引擎 → Hyperbrowser 手动创建一次会话获取 cookie\n"
        "2. 把 cookie 导入 Cookie 池\n"
        "3. 采集任务使用 Playwright tier，让 Stealth 自动处理 cookie 注入\n"
        "4. 或使用 Browser Use tier，让 LLM 自动通过验证码\n"
    ),
}
