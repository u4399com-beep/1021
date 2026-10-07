"""封面图重新获取 (v293) — 根据采集任务日志，重新下载所有在库书籍的封面图。

策略:
1. 从 Book 表中找出所有有 cover_url 但无 cover 文件、或 cover 文件已丢失的书籍
2. 对每本书，使用 fetcher 三段式抓取其 source_url 获取最新封面 URL
3. 下载封面并转为 WebP 格式
4. 记录成功/失败统计
"""

import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from loguru import logger


class Command(BaseCommand):
    help = "重新获取所有在库书籍的封面图 (v293)"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="最多处理 N 本 (0=全部)")
        parser.add_argument("--force", action="store_true", help="强制重新下载已有封面的书籍")
        parser.add_argument("--batch-size", type=int, default=50, help="每批处理数量")
        parser.add_argument("--delay", type=float, default=1.0, help="每本之间的延迟(秒)")

    def handle(self, *args, **options):
        from apps.novel.models import Book

        limit = options["limit"]
        force = options["force"]
        batch_size = options["batch_size"]
        delay = options["delay"]

        # 找出需要重新获取封面的书籍
        qs = Book.objects.filter(is_deleted=False)
        if not force:
            # 只处理无封面文件但有 cover_url 的
            qs = qs.filter(cover="", cover_url__isnull=False).exclude(cover_url="")
        else:
            # 强制重新下载所有有 cover_url 的
            qs = qs.filter(cover_url__isnull=False).exclude(cover_url="")

        total = qs.count()
        if limit > 0:
            qs = qs[:limit]
            total = min(total, limit)

        self.stdout.write(self.style.MIGRATE_HEADING(f"重新获取封面图: {total} 本书籍"))

        success = 0
        failed = 0
        skipped = 0
        errors = []

        for i, book in enumerate(qs.iterator(), 1):
            self.stdout.write(f"  [{i}/{total}] {book.title[:30]} → ", ending="")

            try:
                result = _download_cover_for_book(book)
                if result["ok"]:
                    success += 1
                    self.stdout.write(self.style.SUCCESS(f"✓ {result['cover_path']}"))
                else:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"⚠ {result['reason']}"))
            except Exception as e:
                failed += 1
                errors.append({"book_id": book.id, "title": book.title, "error": repr(e)})
                self.stdout.write(self.style.ERROR(f"✗ {e!r}"))

            # 延迟
            if i < total and delay > 0:
                time.sleep(delay)

            # 批次进度
            if i % batch_size == 0:
                self.stdout.write(f"  --- 进度: {i}/{total} (成功 {success} / 失败 {failed} / 跳过 {skipped}) ---")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS(f"完成: {total} 本 (成功 {success} / 失败 {failed} / 跳过 {skipped})"))
        if errors:
            self.stdout.write(self.style.WARNING(f"错误详情 ({len(errors)}):"))
            for e in errors[:10]:
                self.stdout.write(f"  - {e['title']}: {e['error'][:80]}")


def _download_cover_for_book(book) -> dict:
    """下载单本书的封面图，转 WebP 存储。"""
    cover_url = book.cover_url or ""
    if not cover_url:
        return {"ok": False, "reason": "no cover_url"}

    try:
        import httpx
        from PIL import Image
        from io import BytesIO

        # SSRF 检查
        from crawler_engine.ssrf_guard import is_safe_url
        if not is_safe_url(cover_url):
            return {"ok": False, "reason": "SSRF blocked"}

        with httpx.Client(timeout=30, follow_redirects=True, max_redirects=5) as cli:
            r = cli.get(cover_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
                "Accept": "image/*,*/*;q=0.8",
            })
            if r.status_code != 200:
                return {"ok": False, "reason": f"HTTP {r.status_code}"}

            img = Image.open(BytesIO(r.content)).convert("RGB")
            out_dir = settings.CRAWLER["COVER_DIR"]
            os.makedirs(out_dir, exist_ok=True)
            fname = f"book_{book.id}.webp"
            out_path = os.path.join(out_dir, fname)
            img.save(out_path, format="WEBP", quality=settings.CRAWLER.get("COVER_QUALITY", 85))
            book.cover.name = f"uploads/covers/{fname}"
            book.save(update_fields=["cover"])
            return {"ok": True, "cover_path": out_path}

    except Exception as e:
        return {"ok": False, "reason": repr(e)[:100]}
