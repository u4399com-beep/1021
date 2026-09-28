#!/usr/bin/env python
"""v54-v68 综合端到端测试 (DB-independent)."""
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
    print("v54-v68 综合端到端测试")
    print("="*60)

    section(54, "Book Dedup")
    from apps.novel.dedup import compute_fingerprint, find_duplicates
    fp = compute_fingerprint("斗破苍穹", "天蚕土豆")
    assert_ok("fingerprint is 64 chars", len(fp) == 64)
    assert_ok("same input → same fingerprint", compute_fingerprint("斗破苍穹", "天蚕土豆") == fp)
    assert_ok("different input → different fingerprint", compute_fingerprint("斗破苍穹", "土豆") != fp)

    section(55, "Domain Rate Limiter")
    from apps.crawler_tasks.domain_rate_limiter import acquire_domain_slot, get_domain_wait_time, domain_stats
    assert_ok("acquire_domain_slot callable", callable(acquire_domain_slot))
    assert_ok("get_domain_wait_time callable", callable(get_domain_wait_time))

    section(56, "Chapter Quality Scorer")
    from apps.novel.quality_scorer import score_chapter
    result = score_chapter("<p>这是一段测试文字" * 100 + "</p>")
    assert_ok("score returns dict with score", "score" in result)
    assert_ok("score in 0-100", 0 <= result["score"] <= 100)
    empty = score_chapter("")
    assert_ok("empty content score=0", empty["score"] == 0)

    section(57, "Rule Version Control")
    from apps.crawler_rules.versioning import RuleVersion, save_version, rollback_to_version
    assert_ok("RuleVersion model loaded", RuleVersion._meta.verbose_name == "规则版本")
    assert_ok("save_version callable", callable(save_version))
    assert_ok("rollback_to_version callable", callable(rollback_to_version))

    section(58, "ETA Predictor")
    from apps.crawler_tasks.eta_predictor import predict_eta
    assert_ok("predict_eta callable", callable(predict_eta))

    section(59, "DB Pool")
    from config.db_pool import get_pool_config, diagnostics, POOL_RECOMMENDATIONS
    assert_ok("3 pool configs (small/medium/large)", len(POOL_RECOMMENDATIONS) == 3)
    assert_ok("get_pool_config returns dict", isinstance(get_pool_config("medium"), dict))

    section(60, "API Cache")
    from apps.api.cache_middleware import APICacheMiddleware, cache_diagnostics, _CACHEABLE_PATTERNS
    assert_ok("cacheable patterns exist", len(_CACHEABLE_PATTERNS) >= 5)
    assert_ok("APICacheMiddleware class exists", hasattr(APICacheMiddleware, "__init__"))

    section(61, "Content Segmenter")
    from apps.novel.segmenter import segment_content, segment_stats
    stats = segment_stats("a" * 5000, max_chars=1000)
    assert_ok("5000 chars → 5 segments", stats["estimated_segments"] == 5)
    segs = segment_content("a" * 5000, max_chars=1000)
    assert_ok("segment_content returns list", isinstance(segs, list))

    section(62, "Rule Import/Export")
    from apps.crawler_rules.io import export_rules, import_rules
    assert_ok("export_rules callable", callable(export_rules))
    assert_ok("import_rules callable", callable(import_rules))

    section(63, "Traffic Stats")
    from apps.sites.traffic_stats import PageView, record_page_view, traffic_summary
    assert_ok("PageView model loaded", PageView._meta.verbose_name == "页面浏览")
    assert_ok("record_page_view callable", callable(record_page_view))

    section(64, "Auto Priority")
    from apps.crawler_tasks.auto_priority import adjust_priorities
    assert_ok("adjust_priorities callable", callable(adjust_priorities))

    section(65, "Update Detector")
    from apps.novel.update_detector import detect_new_chapters
    assert_ok("detect_new_chapters callable", callable(detect_new_chapters))

    section(66, "Multi-level Cache")
    from apps.sites.multilevel_cache import get_cached, set_cached, compute_etag, check_etag, cache_stats
    set_cached("test_key", {"value": 42}, ttl=60)
    val = get_cached("test_key")
    assert_ok("set+get works", val == {"value": 42})
    etag = compute_etag("hello")
    assert_ok("etag is 32 chars hex", len(etag) == 32)
    stats = cache_stats()
    assert_ok("cache_stats returns dict", "local_cache_size" in stats)

    section(67, "Integrity Check")
    from apps.novel.integrity_check import check_integrity, repair_stale_counts
    assert_ok("check_integrity callable", callable(check_integrity))
    assert_ok("repair_stale_counts callable", callable(repair_stale_counts))

    section(68, "Test Script + Deploy")
    from django.apps import apps
    total = len(apps.get_models())
    print(f"  Total Django models: {total}")
    assert_ok("models >= 50", total >= 50)

    from config.urls import urlpatterns
    print(f"  Root URL patterns: {len(urlpatterns)}")
    assert_ok("URL patterns >= 23", len(urlpatterns) >= 23)

    from apps.themes.engine import THEME_TEMPLATES
    assert_ok("6 themes registered", len(THEME_TEMPLATES) >= 6)
    assert_ok("uaa_clone theme registered", "uaa_clone" in THEME_TEMPLATES)

    print("\n" + "="*60)
    print("✓ v54-v68 综合测试全部通过")
    print("="*60)
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}"); sys.exit(2)
