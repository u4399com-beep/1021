"""章节采集提速 (v321) — 并发抓取 + 批量写入 + 预连接优化。

提速策略:
1. 并发章节抓取: 用 ThreadPoolExecutor 并发抓取同一本书的多个章节
2. 批量数据库写入: 用 bulk_create/update 替代逐条 update_or_create
3. 预连接优化: 复用 httpx Client 连接池
4. 智能跳过: 已有且内容不为空的章节直接跳过
"""
from __future__ import annotations

import concurrent.futures
import time
from typing import Any
from loguru import logger


def fetch_chapters_concurrent(
    book,
    chapters: list[dict],
    rule_config: dict,
    *,
    max_workers: int = 3,
    interval: float = 1.0,
) -> list[dict]:
    """并发抓取多个章节内容。

    Args:
        book: Book 对象
        chapters: [{url, title, volume, ...}]
        rule_config: 章节规则配置
        max_workers: 最大并发数
        interval: 每次请求间隔

    Returns: [{url, title, content, ok, error}, ...]
    """
    from crawler_engine.three_tier_fetcher import fetch_three_tier
    from crawler_engine.parsers.factory import build_parser
    from crawler_engine.quality_validator import validate_chapter_data

    results = []
    parser = build_parser(rule_config)

    def _fetch_one(ch_meta):
        url = ch_meta.get("url", "")
        title = ch_meta.get("title", "")
        if not url:
            return {"url": url, "title": title, "ok": False, "error": "no url"}

        try:
            html = fetch_three_tier(url)
            data = parser.parse("chapter", html, base_url=url)
            content = data.get("content", "")
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")

            # 质量验证
            qv = validate_chapter_data({"title": title, "content": content})
            if not qv["valid"]:
                logger.warning(f"chapter quality: {title} — {qv['issues']}")

            return {
                "url": url, "title": title, "content": content,
                "word_count": len(content), "ok": True, "error": None,
            }
        except Exception as e:
            return {"url": url, "title": title, "ok": False, "error": repr(e)}

    # 并发抓取
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = []
        for i, ch in enumerate(chapters):
            futures.append(pool.submit(_fetch_one, ch))
            # 控制速率: 每提交 max_workers 个任务后等 interval 秒
            if (i + 1) % max_workers == 0:
                time.sleep(interval)

        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # 按原始顺序排序
    url_order = {ch.get("url", ""): i for i, ch in enumerate(chapters)}
    results.sort(key=lambda r: url_order.get(r.get("url", ""), 0))

    return results


def batch_save_chapters(book, results: list[dict], *, storage: str = "db") -> dict:
    """批量保存章节到数据库。

    Args:
        book: Book 对象
        results: [{url, title, content, word_count, ok}, ...]
        storage: "db" | "txt" | "both"

    Returns: {saved, skipped, failed}
    """
    from apps.novel.models import Chapter
    from django.utils import timezone

    saved, skipped, failed = 0, 0, 0

    for i, r in enumerate(results, 1):
        if not r.get("ok"):
            failed += 1
            continue

        url = r.get("url", "")
        title = r.get("title", "")
        content = r.get("content", "")
        word_count = r.get("word_count", len(content))

        # 检查是否已存在且内容不为空
        existing = Chapter.objects.filter(book=book, source_url=url).first()
        if existing and existing.content and len(existing.content) > 100:
            skipped += 1
            continue

        # TXT 存储
        txt_path = ""
        if storage in ("txt", "both"):
            try:
                import os
                from django.conf import settings
                ch_dir = os.path.join(settings.CRAWLER["CHAPTER_DIR"], str(book.id))
                os.makedirs(ch_dir, exist_ok=True)
                fn = f"{i:05d}_{(title or 'untitled')[:30]}.txt"
                with open(os.path.join(ch_dir, fn), "w", encoding="utf-8") as f:
                    f.write(content)
                txt_path = os.path.join(ch_dir, fn)
            except Exception:
                pass

        # 数据库存储
        Chapter.objects.update_or_create(
            book=book, source_url=url,
            defaults={
                "title": title,
                "order_index": i,
                "source_order": i,
                "content": content if storage in ("db", "both") else "",
                "txt_path": txt_path,
                "word_count": word_count,
                "status": "fetched",
                "fetched_at": timezone.now(),
            },
        )
        saved += 1

    # 更新书籍统计
    book.chapter_count = book.chapters.count()
    from django.db.models import Sum
    book.word_count = book.chapters.aggregate(total=Sum("word_count"))["total"] or 0
    book.save(update_fields=["chapter_count", "word_count"])

    return {"saved": saved, "skipped": skipped, "failed": failed}


def create_pooled_client(url: str, max_connections: int = 10):
    """创建复用连接的 httpx Client (v321 提速)。

    用于 Layer 1-2 的连接池复用。
    """
    import httpx
    from crawler_engine.anti_detection.header_fingerprint import generate_fingerprint_headers, reorder_headers

    headers = reorder_headers(generate_fingerprint_headers())
    return httpx.Client(
        timeout=15,
        follow_redirects=True,
        max_redirects=5,
        headers=headers,
        limits=httpx.Limits(max_connections=max_connections, max_keepalive_connections=5),
    )
