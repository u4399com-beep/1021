"""yckceo/Legado 书源格式转换器 (v318) — 将开源阅读书源 JSON 转换为本系统规则格式。

支持的开源阅读书源格式:
{
  "bookSourceName": "站点名",
  "bookSourceUrl": "https://www.example.com",
  "rule": {
    "bookList": "@css:ul.book-list li",
    "name": "@css:h3::text",
    "author": "@css:.author::text",
    "intro": "@css:.intro::text",
    "coverUrl": "@css:img::attr(src)",
    "bookUrl": "@css:a::attr(href)",
    "tocUrl": "@css:a[href*=chapter]::attr(href)",
    "chapterList": "@css:ul.chapter-list li",
    "chapterName": "@css:a::text",
    "chapterUrl": "@css:a::attr(href)",
    "content": "@css:div.content"
  }
}

本系统格式:
- list rule: {item_selector, book_url, book_title, ...}
- book rule: {title, author, cover, intro, ...}
- toc rule: {item_selector, chapter_url, chapter_title, ...}
- chapter rule: {title, content, ...}
"""
from __future__ import annotations
import re
from typing import Any


def _parse_selector(sel_str: str) -> dict:
    """解析开源阅读选择器字符串为本系统格式。

    支持前缀:
    - @css: → {type: "css", expr: "..."}
    - @xpath: → {type: "xpath", expr: "..."}
    - 正则表达式 → {type: "regex", expr: "..."}
    - 纯文本 → {type: "css", expr: "..."}
    """
    if not sel_str:
        return {}

    sel = sel_str.strip()

    # @css: 前缀
    if sel.startswith("@css:"):
        expr = sel[5:].strip()
        # 处理 ::text 和 ::attr() 伪元素
        return {"type": "css", "expr": expr}

    # @xpath: 前缀
    if sel.startswith("@xpath:"):
        expr = sel[7:].strip()
        return {"type": "xpath", "expr": expr}

    # @json: 前缀
    if sel.startswith("@json:"):
        expr = sel[6:].strip()
        return {"type": "json_path", "expr": expr}

    # 正则表达式 (以 ^ 或 \\ 开头)
    if sel.startswith("^") or sel.startswith("\\"):
        return {"type": "regex", "expr": sel}

    # 默认当 CSS 处理
    return {"type": "css", "expr": sel}


def convert_yckceo_to_rules(source_json: dict) -> dict:
    """将 yckceo/Legado 书源 JSON 转换为本系统 4 套规则配置。

    Args:
        source_json: 开源阅读书源 JSON dict

    Returns: {
        source: {name, host, ...},
        list_config: {...},
        book_config: {...},
        toc_config: {...},
        chapter_config: {...},
    }
    """
    rule = source_json.get("rule", {})
    source_url = source_json.get("bookSourceUrl", "")
    source_name = source_json.get("bookSourceName", "")

    # 提取 host
    host = ""
    if source_url:
        from urllib.parse import urlparse
        host = urlparse(source_url).netloc

    # ─── 列表页规则 ───
    list_config = {}
    if rule.get("bookList"):
        list_config["item_selector"] = _parse_selector(rule["bookList"])
    if rule.get("bookUrl"):
        list_config["book_url"] = _parse_selector(rule["bookUrl"])
    if rule.get("name"):
        list_config["book_title"] = _parse_selector(rule["name"])
    if rule.get("author"):
        list_config["book_author"] = _parse_selector(rule["author"])
    if rule.get("coverUrl"):
        list_config["book_cover"] = _parse_selector(rule["coverUrl"])
    if rule.get("intro"):
        list_config["book_intro"] = _parse_selector(rule["intro"])
    # 列表页分页
    if rule.get("bookListNextUrl"):
        list_config["next_page"] = _parse_selector(rule["bookListNextUrl"])

    # ─── 书籍信息页规则 ───
    book_config = {}
    if rule.get("name"):
        book_config["title"] = _parse_selector(rule["name"])
    if rule.get("author"):
        book_config["author"] = _parse_selector(rule["author"])
    if rule.get("coverUrl"):
        book_config["cover"] = _parse_selector(rule["coverUrl"])
    if rule.get("intro"):
        book_config["intro"] = _parse_selector(rule["intro"])
    if rule.get("kind"):
        book_config["category"] = {**_parse_selector(rule["kind"]), "multi": True}
    if rule.get("lastChapter"):
        book_config["last_chapter_title"] = _parse_selector(rule["lastChapter"])
    if rule.get("tocUrl"):
        book_config["toc_url"] = _parse_selector(rule["tocUrl"])
    if rule.get("status"):
        book_config["status"] = _parse_selector(rule["status"])

    # ─── 章节目录规则 ───
    toc_config = {}
    if rule.get("chapterList"):
        toc_config["item_selector"] = _parse_selector(rule["chapterList"])
    if rule.get("chapterUrl"):
        toc_config["chapter_url"] = _parse_selector(rule["chapterUrl"])
    if rule.get("chapterName"):
        toc_config["chapter_title"] = _parse_selector(rule["chapterName"])
    # 分卷检测
    if rule.get("volume"):
        toc_config["volume_selector"] = _parse_selector(rule["volume"])
    # 目录分页
    if rule.get("chapterListNextUrl") or rule.get("nextTocUrl"):
        next_sel = rule.get("chapterListNextUrl") or rule.get("nextTocUrl")
        toc_config["next_page"] = _parse_selector(next_sel)

    # ─── 章节内容规则 ───
    chapter_config = {}
    if rule.get("chapterName"):
        chapter_config["title"] = _parse_selector(rule["chapterName"])
    if rule.get("content"):
        chapter_config["content"] = _parse_selector(rule["content"])
    # 章节分页
    if rule.get("contentNextUrl"):
        chapter_config["next_page"] = _parse_selector(rule["contentNextUrl"])

    # ─── 反爬配置 ───
    anti_detection = {
        "tier_required": "auto",
        "cookie_required": bool(source_json.get("loginUrl")),
        "waf_captcha": False,
        "encoding": "auto",
    }

    # 如果有 loginUrl，说明需要 cookie
    if source_json.get("loginUrl"):
        anti_detection["cookie_required"] = True
        anti_detection["tier_required"] = "playwright"

    return {
        "source": {
            "name": source_name,
            "host": host,
            "enabled": True,
            "anti_detection": anti_detection,
            "notes": f"Converted from yckceo/Legado book source",
        },
        "list_config": list_config,
        "book_config": book_config,
        "toc_config": toc_config,
        "chapter_config": chapter_config,
    }


def convert_and_import(source_json: dict, overwrite: bool = False) -> dict:
    """转换并导入到数据库。

    Returns: {source_id, rules_created, errors}
    """
    from apps.crawler_rules.models import CrawlerRule, CrawlerSource

    result = convert_yckceo_to_rules(source_json)
    src_data = result["source"]

    # 创建/更新 source
    source, created = CrawlerSource.objects.update_or_create(
        host=src_data["host"],
        defaults={
            "name": src_data["name"],
            "enabled": True,
            "anti_detection": src_data["anti_detection"],
            "notes": src_data["notes"],
        },
    )

    rules_created = 0
    errors = []

    for target, name_prefix, config in [
        ("list", "列表页", result["list_config"]),
        ("book", "书籍页", result["book_config"]),
        ("toc", "章节目录", result["toc_config"]),
        ("chapter", "章节内容", result["chapter_config"]),
    ]:
        if not config:
            continue
        rule_name = f"{src_data['name']} - {name_prefix}"
        try:
            rule, rule_created = CrawlerRule.objects.update_or_create(
                name=rule_name,
                defaults={
                    "source": source,
                    "target": target,
                    "config": config,
                    "enabled": True,
                    "priority": 100,
                },
            )
            rules_created += 1
        except Exception as e:
            errors.append(f"{name_prefix}: {e!r}")

    return {
        "source_id": source.id,
        "source_name": source.name,
        "rules_created": rules_created,
        "errors": errors,
    }
