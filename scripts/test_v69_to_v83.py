#!/usr/bin/env python
"""v69-v83 综合端到端测试 (DB-independent)."""
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
    print("v69-v83 综合端到端测试")
    print("="*60)

    section(69, "AI Rule Generation")
    from apps.crawler_rules.ai.rule_generator import generate_list_rule, generate_book_rule, generate_chapter_rule
    # Test with sample HTML
    sample_html = '<ul class="book-list"><li><a href="/book/1"><h3>斗破苍穹</h3></a><span class="author">天蚕土豆</span></li><li><a href="/book/2"><h3>凡人修仙传</h3></a><span class="author">忘语</span></li><li><a href="/book/3"><h3>遮天</h3></a><span class="author">辰东</span></li><li><a href="/book/4"><h3>完美世界</h3></a><span class="author">辰东</span></li><li><a href="/book/5"><h3>莽荒纪</h3></a><span class="author">我吃西红柿</span></li></ul>'
    result = generate_list_rule(sample_html)
    assert_ok("list rule generated", "config" in result)
    assert_ok("items found >= 5", result.get("items_found", 0) >= 5)

    section(70, "Advertising")
    from apps.sites.advertising import AdSlot, get_ads_for_page
    assert_ok("AdSlot model loaded", AdSlot._meta.verbose_name == "广告位")

    section(71, "Membership")
    from apps.account.membership import ReaderProfile, Bookshelf, ReadingHistory
    assert_ok("ReaderProfile model loaded", ReaderProfile._meta.verbose_name == "读者账户")
    assert_ok("Bookshelf model loaded", Bookshelf._meta.verbose_name == "书架")

    section(72, "Payments")
    from apps.account.payments import PaymentOrder, PaidChapter, create_order, mark_paid
    assert_ok("PaymentOrder model loaded", PaymentOrder._meta.verbose_name == "支付订单")

    section(73, "Mobile API")
    from apps.api.mobile import mobile_home, mobile_book_detail, mobile_chapter_content, mobile_search
    assert_ok("mobile_home callable", callable(mobile_home))
    assert_ok("mobile_search callable", callable(mobile_search))

    section(74, "Distributed")
    from apps.crawler_tasks.distributed import register_worker, heartbeat, cluster_stats
    register_worker("test-worker", ["crawler"], max_concurrency=4)
    heartbeat("test-worker")
    stats = cluster_stats()
    assert_ok("cluster_stats returns dict", isinstance(stats, dict))
    assert_ok("active_workers >= 1", stats.get("active_workers", 0) >= 1)

    section(75, "Migrator")
    from apps.novel.migrator import import_books_from_json, import_from_csv_format
    assert_ok("import_books callable", callable(import_books_from_json))

    section(76, "WebSocket Notify")
    from apps.dashboard.ws_notify import publish_notification, get_recent_notifications
    publish_notification("test.event", {"key": "value"})
    notifs = get_recent_notifications()
    assert_ok("notification published + retrieved", len(notifs) > 0)

    section(77, "Preset Library")
    from apps.crawler_rules.preset_library import PRESETS, get_preset, list_presets
    assert_ok("5+ presets available", len(PRESETS) >= 5)
    assert_ok("cunshu_la preset exists", "cunshu_la" in PRESETS)
    assert_ok("generic_php preset exists", "generic_php" in PRESETS)

    section(78, "Reading Themes")
    from apps.novel.reading_prefs import THEMES, get_theme, apply_to_html
    assert_ok("5 reading themes", len(THEMES) >= 5)
    assert_ok("night theme exists", "night" in THEMES)
    html = apply_to_html("<p>test</p>", "night")
    assert_ok("apply_to_html wraps content", "reading-content" in html)

    section(79, "Log Stream")
    from apps.crawler_tasks.log_stream import task_log_stream
    assert_ok("task_log_stream callable", callable(task_log_stream))

    section(80, "Book Ratings")
    from apps.novel.ratings import BookRating, update_book_aggregate_rating
    assert_ok("BookRating model loaded", BookRating._meta.verbose_name == "书籍评分")

    section(81, "Tag Extraction")
    from apps.novel.tag_extractor import extract_keywords
    kws = extract_keywords("斗气化马斗破苍穹修炼升级斗帝境界突破", top_n=5)
    assert_ok("extract_keywords returns list", isinstance(kws, list))
    assert_ok("keywords found >= 1", len(kws) >= 1)

    section(82, "Benchmark")
    from apps.dashboard.benchmark import benchmark_url
    assert_ok("benchmark_url callable", callable(benchmark_url))

    section(83, "Test Script + Final Check")
    from django.apps import apps
    total = len(apps.get_models())
    print(f"  Total Django models: {total}")
    assert_ok("models >= 55", total >= 55)

    from config.urls import urlpatterns
    print(f"  Root URL patterns: {len(urlpatterns)}")
    assert_ok("URL patterns >= 23", len(urlpatterns) >= 23)

    from apps.themes.engine import THEME_TEMPLATES
    assert_ok("6 themes registered", len(THEME_TEMPLATES) >= 6)

    print("\n" + "="*60)
    print("✓ v69-v83 综合测试全部通过")
    print("="*60)
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}"); sys.exit(2)
