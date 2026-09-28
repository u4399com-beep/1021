"""Preset rule library (v77) — common site rule templates."""


PRESETS = {
    "qidian": {
        "name": "起点中文网",
        "host": "www.qidian.com",
        "list_config": {
            "item_selector": {"type": "css", "expr": "div.book-img-text li"},
            "book_url": {"type": "xpath", "expr": ".//a/@href"},
            "book_title": {"type": "css", "expr": "h4 a::text"},
            "book_author": {"type": "css", "expr": ".author::text"},
        },
        "book_config": {
            "title": {"type": "css", "expr": "h1::text"},
            "author": {"type": "css", "expr": ".writer-name::text"},
            "intro": {"type": "css", "expr": ".book-intro::text"},
        },
    },
    "zongheng": {
        "name": "纵横中文网",
        "host": "www.zongheng.com",
        "list_config": {
            "item_selector": {"type": "css", "expr": "div.book-item"},
            "book_url": {"type": "xpath", "expr": ".//a/@href"},
            "book_title": {"type": "css", "expr": ".book-name::text"},
        },
    },
    "17k": {
        "name": "17K小说网",
        "host": "www.17k.com",
        "list_config": {
            "item_selector": {"type": "css", "expr": "ul.list li"},
            "book_url": {"type": "xpath", "expr": ".//a/@href"},
            "book_title": {"type": "css", "expr": "a::text"},
        },
    },
    "cunshu_la": {
        "name": "存书啦",
        "host": "www.cunshu.la",
        "list_config": {
            "item_selector": {"type": "css", "expr": "ul.library-list li"},
            "book_url": {"type": "xpath", "expr": ".//a/@href"},
        },
        "anti_detection": {"tier_required": "playwright", "waf_captcha": True},
    },
    "generic_php": {
        "name": "通用PHP小说站",
        "host": "",
        "list_config": {
            "item_selector": {"type": "css", "expr": "ul.book-list li, div.book-item, table.list tr[class]"},
            "book_url": {"type": "xpath", "expr": ".//a/@href"},
            "book_title": {"type": "css", "expr": "h3::text, .title::text, a::text"},
        },
        "book_config": {
            "title": {"type": "css", "expr": "h1::text"},
            "author": {"type": "css", "expr": ".author::text"},
            "content": {"type": "css", "expr": "div.content, div#content, div#BookText"},
        },
    },
}


def get_preset(name: str) -> dict | None:
    return PRESETS.get(name)


def list_presets() -> list[dict]:
    return [{"key": k, "name": v["name"], "host": v.get("host", "")} for k, v in PRESETS.items()]
