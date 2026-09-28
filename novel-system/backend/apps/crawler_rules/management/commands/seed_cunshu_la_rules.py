"""Import cunshu.la crawler rules into the DB.

Usage:
    python manage.py seed_cunshu_la_rules

This creates:
  - One CrawlerSource record for cunshu.la
  - Four CrawlerRule records (list / book / toc / chapter)
  - If the source already exists, rules are updated in place.

After importing, you can test the rules in the admin UI:
  System settings → 采集规则 → 选择 cunshu.la 列表页规则 → 测试 → 填入
  https://www.cunshu.la/library.php?sort=latest&page=1
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.crawler_rules.models import CrawlerRule, CrawlerSource
from apps.crawler_rules.presets.cunshu_la import (
    ANTI_DETECTION_HINTS,
    BOOK_CONFIG,
    CHAPTER_CONFIG,
    LIST_CONFIG,
    TOC_CONFIG,
)


class Command(BaseCommand):
    help = "Import cunshu.la crawler rules (list / book / toc / chapter)."

    def handle(self, *args, **options):
        # 1. Create source
        source, created = CrawlerSource.objects.update_or_create(
            host="www.cunshu.la",
            defaults={
                "name": "存书啦 (cunshu.la)",
                "enabled": True,
                "anti_detection": ANTI_DETECTION_HINTS,
                "notes": (
                    "PHP + GoEdge WAF 站点。建议使用 Playwright+Stealth 或 Browser Use tier。"
                    "首次抓取需要通过验证码 — 通过 Hyperbrowser 创建会话获取 cookie，"
                    "或人工访问一次后导出 cookie 到 Cookie 池。"
                ),
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ 创建采集源: {source.host}"))
        else:
            self.stdout.write(f"  ~ 已存在采集源: {source.host}")

        # 2. Create 4 rules
        rules_data = [
            ("list",    "cunshu.la - 列表页",  LIST_CONFIG,    100),
            ("book",    "cunshu.la - 书籍页",  BOOK_CONFIG,    100),
            ("toc",     "cunshu.la - 章节目录", TOC_CONFIG,    100),
            ("chapter", "cunshu.la - 章节内容", CHAPTER_CONFIG, 100),
        ]
        for target, name, config, prio in rules_data:
            rule, created = CrawlerRule.objects.update_or_create(
                name=name,
                defaults={
                    "source": source,
                    "target": target,
                    "enabled": True,
                    "priority": prio,
                    "config": config,
                    "notes": f"Imported by `seed_cunshu_la_rules` command.",
                },
            )
            tag = "+" if created else "~"
            self.stdout.write(f"  {tag} {target:8s} → {name}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("✓ cunshu.la 规则导入完成"))
        self.stdout.write("")
        self.stdout.write("下一步:")
        self.stdout.write("  1. 后台 → 采集规则 → 选择 'cunshu.la - 列表页' → 测试")
        self.stdout.write("  2. 测试 URL: https://www.cunshu.la/library.php?sort=latest&page=1")
        self.stdout.write("  3. 测试时使用 Playwright tier（系统设置 → 采集引擎 → 选 playwright）")
        self.stdout.write("  4. 若 403，先在 Hyperbrowser 创建会话获取 cookie")
        self.stdout.write("  5. 规则可反复调整后再次运行本命令覆盖更新")
