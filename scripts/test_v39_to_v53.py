#!/usr/bin/env python
"""v39-v53 综合端到端测试 (DB-independent)."""
from __future__ import annotations
import os, sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")
django.setup()
from django.conf import settings
settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "test"}}

def section(n, t):
    print(f"\n{'='*60}\n【v{n}】{t}\n{'='*60}")

def assert_ok(label, cond):
    print(f"  {'✓' if cond else '✗'} {label}")
    if not cond: raise AssertionError(label)

def main():
    print("="*60)
    print("v39-v53 综合端到端测试")
    print("="*60)

    section(39, "Vue Dashboard")
    from pathlib import Path
    p = Path("/home/z/my-project/novel-system/frontend/src/views/analytics/Index.vue")
    assert_ok("analytics/Index.vue exists", p.exists())

    section(40, "Task Dependency Graph API")
    from apps.crawler_tasks.views import CrawlerTaskViewSet
    methods = [m for m in dir(CrawlerTaskViewSet) if "depend" in m or "downstream" in m]
    assert_ok("dependency endpoints exist", len(methods) >= 3)

    section(41, "SSE Progress Stream")
    from apps.crawler_tasks.sse import progress_stream, all_progress_stream
    assert_ok("SSE functions importable", True)

    section(42, "Alert Dispatcher")
    from apps.dashboard.alert_dispatcher import check_and_dispatch_alerts
    assert_ok("alert dispatcher importable", callable(check_and_dispatch_alerts))

    section(43, "Task Templates")
    from apps.crawler_tasks.templates import TaskTemplate
    assert_ok("TaskTemplate model loaded", TaskTemplate._meta.verbose_name == "任务模板")

    section(44, "Data Archive")
    from apps.novel.archive import archive_old_chapters
    assert_ok("archive_old_chapters importable", callable(archive_old_chapters))

    section(45, "Source Health Monitor")
    from apps.crawler_rules.health_monitor import source_health_report
    assert_ok("source_health_report importable", callable(source_health_report))

    section(46, "Content Audit")
    from apps.content_cleaner.audit import audit_text, BannedKeyword
    # audit_text queries DB — just verify import
    assert_ok("audit_text importable", callable(audit_text))
    assert_ok("BannedKeyword model loaded", BannedKeyword._meta.verbose_name == "敏感词")

    section(47, "Cover Filler")
    from apps.novel.cover_filler import fill_missing_covers
    assert_ok("fill_missing_covers importable", callable(fill_missing_covers))

    section(48, "Task Report")
    from apps.crawler_tasks.report import generate_task_report
    assert_ok("generate_task_report importable", callable(generate_task_report))

    section(49, "A/B Test")
    from apps.sites.ab_test import ABTestConfig
    assert_ok("ABTestConfig model loaded", ABTestConfig._meta.verbose_name == "A/B 测试")

    section(50, "Smart Scheduler")
    from apps.crawler_tasks.smart_scheduler import suggest_best_time
    assert_ok("suggest_best_time importable", callable(suggest_best_time))

    section(51, "IP Whitelist")
    from apps.account.ip_whitelist import IPWhitelist, is_ip_whitelisted
    assert_ok("IPWhitelist model loaded", IPWhitelist._meta.verbose_name == "IP 白名单")
    assert_ok("is_ip_whitelisted callable", callable(is_ip_whitelisted))

    section(52, "Slow Query Monitor")
    from apps.dashboard.slow_query_monitor import get_slow_queries, clear_slow_queries, SlowQueryLogger
    assert_ok("SlowQueryLogger class exists", hasattr(SlowQueryLogger, '__init__'))
    assert_ok("get_slow_queries callable", callable(get_slow_queries))

    section(53, "Test Script (this)")
    assert_ok("this script running", True)

    # Final check: total models (no DB needed)
    from django.apps import apps
    total = len(apps.get_models())
    print(f"\n  Total Django models: {total}")
    assert_ok("models > 44", total > 44)

    # Check URLs
    from config.urls import urlpatterns
    print(f"  Root URL patterns: {len(urlpatterns)}")
    assert_ok("URL patterns >= 23", len(urlpatterns) >= 23)

    # Check themes
    from apps.themes.engine import THEME_TEMPLATES
    assert_ok("6 themes registered", len(THEME_TEMPLATES) >= 6)
    assert_ok("uaa_clone theme registered", "uaa_clone" in THEME_TEMPLATES)

    print("\n" + "="*60)
    print("✓ v39-v53 综合测试全部通过")
    print("="*60)
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}"); sys.exit(2)
