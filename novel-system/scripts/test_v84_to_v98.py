#!/usr/bin/env python
"""v84-v98 综合端到端测试 (DB-independent)."""
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
    print("v84-v98 综合端到端测试")
    print("="*60)

    section(84, "Sitemap Priority")
    from apps.seo.sitemap_priority import compute_priority, get_prioritized_books
    assert_ok("compute_priority callable", callable(compute_priority))

    section(85, "Content Similarity")
    from apps.novel.similarity import content_hash, similarity_ratio, is_likely_duplicate
    h1 = content_hash("test content")
    h2 = content_hash("test content")
    h3 = content_hash("different")
    assert_ok("same content → same hash", h1 == h2)
    assert_ok("different content → different hash", h1 != h3)
    assert_ok("similarity_ratio returns float", isinstance(similarity_ratio("a", "b"), float))

    section(86, "Task Presets")
    from apps.crawler_tasks.task_presets import TASK_PRESETS, get_preset, list_presets
    assert_ok("5+ presets available", len(TASK_PRESETS) >= 5)
    assert_ok("full_crawl preset exists", "full_crawl" in TASK_PRESETS)
    assert_ok("stealth_mode preset exists", "stealth_mode" in TASK_PRESETS)

    section(87, "Reader Auth")
    from apps.account.reader_auth import reader_login, reader_register
    assert_ok("reader_login callable", callable(reader_login))
    assert_ok("reader_register callable", callable(reader_register))

    section(88, "Bookshelf Sync")
    from apps.account.bookshelf_api import get_bookshelf, add_to_bookshelf, remove_from_bookshelf
    assert_ok("get_bookshelf callable", callable(get_bookshelf))
    assert_ok("add_to_bookshelf callable", callable(add_to_bookshelf))

    section(89, "Reading History")
    from apps.account.bookshelf_api import get_reading_history, update_reading_progress
    assert_ok("get_reading_history callable", callable(get_reading_history))
    assert_ok("update_reading_progress callable", callable(update_reading_progress))

    section(90, "Recommendations")
    from apps.novel.recommendations import recommend_for_reader
    assert_ok("recommend_for_reader callable", callable(recommend_for_reader))

    section(91, "Chapter Comments")
    from apps.novel.comments import ChapterComment
    assert_ok("ChapterComment model loaded", ChapterComment._meta.verbose_name == "章节评论")

    section(92, "Rankings")
    from apps.novel.rankings import get_ranking
    assert_ok("get_ranking callable", callable(get_ranking))

    section(93, "Batch Rule Test")
    from apps.crawler_rules.batch_test import batch_test_source
    assert_ok("batch_test_source callable", callable(batch_test_source))

    section(94, "Site Config IO")
    from apps.sites.config_io import export_site_config, import_site_config
    assert_ok("export_site_config callable", callable(export_site_config))
    assert_ok("import_site_config callable", callable(import_site_config))

    section(95, "Execution Estimate")
    from apps.crawler_tasks.execution_estimate import estimate_execution
    est = estimate_execution(100, 3.0, 5)
    assert_ok("estimate returns dict", isinstance(est, dict))
    assert_ok("estimated_seconds > 0", est["estimated_seconds"] > 0)

    section(96, "Theme Color Customizer")
    from apps.themes.color_customizer import COLOR_SCHEMES, get_scheme, list_schemes, generate_css
    assert_ok("7+ color schemes", len(COLOR_SCHEMES) >= 7)
    css = generate_css("uaa_blue")
    assert_ok("generate_css returns CSS with :root", ":root" in css)

    section(97, "Health Probe")
    from apps.dashboard.health_probe import health_probe
    assert_ok("health_probe callable", callable(health_probe))

    section(98, "Final Check")
    from django.apps import apps
    total = len(apps.get_models())
    print(f"  Total Django models: {total}")
    assert_ok("models >= 57", total >= 57)

    from apps.themes.engine import THEME_TEMPLATES
    assert_ok("6 themes registered", len(THEME_TEMPLATES) >= 6)

    print("\n" + "="*60)
    print("✓ v84-v98 综合测试全部通过")
    print("="*60)
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}"); sys.exit(2)
