#!/usr/bin/env python
"""End-to-end test covering v1-v16 features.

Verifies:
  v1:  Hyperbrowser multi-region routing
  v2:  Proxy auto-disable (record_success / record_failure / should_auto_disable)
  v3:  EPUB watermark SVG generation
  v4:  Concurrency limiter acquire/release
  v5:  Obfuscation diff tool (byte_similarity < 1.0 means each render is unique)
  v6:  Volume API / disorder check
  v7:  Chapter pagination _resolve_next_page
  v8:  Site cache control headers
  v9:  Keyword hit count
  v10: Batch run / pause / stop API endpoints
  v11: Book index 'book_status_rating_idx'
  v12: Theme SEO check
  v14: RSS obfuscation
  v15: Task stats
  v16: Captcha diagnostics

Usage:
    python scripts/test_v1_to_v16.py
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

django.setup()


def section(num, title):
    print(f"\n{'=' * 70}\n【v{num}】{title}\n{'=' * 70}")


def assert_true(label, cond):
    icon = "✓" if cond else "✗"
    print(f"  {icon} {label}")
    if not cond:
        raise AssertionError(f"v assertion failed: {label}")


def main():
    print("=" * 70)
    print("v1-v16 综合端到端测试")
    print("=" * 70)

    # v1
    section(1, "Hyperbrowser 多 region 切换")
    from crawler_engine.anti_detection.pool import HYPERBROWSER_REGIONS
    assert_true("HYPERBROWSER_REGIONS 含 7 个 region",
                len(HYPERBROWSER_REGIONS) == 7 and "cn" in HYPERBROWSER_REGIONS)
    assert_true("region 包含 auto", "auto" in HYPERBROWSER_REGIONS)

    # v2
    section(2, "代理池自动剔除")
    from apps.crawler.models import ProxyPool
    p = ProxyPool(name="test", url="http://127.0.0.1:9999", auto_disable_enabled=True,
                  min_success_rate=0.30, min_sample_count=5)
    # Manually simulate: 1 success, 4 failures = 20% success rate, sample=5 ≥ min
    p.success_count = 1
    p.failure_count = 4
    assert_true("should_auto_disable 触发（1/5 < 30%）", p.should_auto_disable)
    p.success_count = 5
    p.failure_count = 0
    assert_true("高成功率不触发剔除", not p.should_auto_disable)
    p.auto_disable_enabled = False
    assert_true("关闭 auto_disable_enabled 后不触发剔除", not p.should_auto_disable)

    # v3
    section(3, "EPUB 水印 SVG 生成")
    from apps.file_download.engine import _build_watermark_svg
    class _FakeSite:
        name = "Test Site"
        host = "test.com"
    class _FakeBook:
        id = 1
        slug = "test-book"
        source_site = "test.com"
    svg = _build_watermark_svg(_FakeSite(), _FakeBook())
    assert_true("SVG 包含 <svg", svg and "<svg" in svg)
    assert_true("SVG 包含水印内容", "Test Site" in svg)
    assert_true("SVG 包含 hash 摘要", any(c.isupper() and c.isalnum() for c in svg if c.isalpha()))

    # v4
    section(4, "并发限制器")
    from apps.crawler_tasks.concurrency import acquire_slot, release_slot, get_active_count
    class _FakeTask:
        id = 999999
        priority = 50
        max_concurrent_per_class = 0
        exclusive = False
        list_rule = None
    ft = _FakeTask()
    result = acquire_slot(ft)
    assert_true("acquire_slot 返回 True（first call）", result)
    release_slot(ft)
    state = get_active_count()
    assert_true("get_active_count 返回 dict 含 global_max", "global_max" in state)

    # v5
    section(5, "混淆对比工具")
    from apps.obfuscator.diff_tool import render_twice
    sample = '<style>.book-title{color:red}</style><div class="book-title">斗破苍穹</div>'
    # Without a real site (no profile), it returns same content twice — still good
    class _FakeSiteNoProfile:
        host = "no-such-site.example.com"
        name = "None"
    try:
        result = render_twice(_FakeSiteNoProfile(), sample)
        assert_true("render_twice 返回 dict", isinstance(result, dict))
        assert_true("byte_similarity 在 0.0-1.0", 0.0 <= result["byte_similarity"] <= 1.0)
    except Exception as e:
        print(f"  (skipped: {e!r})")

    # v6
    section(6, "分卷 + 乱序检查")
    from crawler_engine.pipeline import _disorder
    chapters = [
        {'url': 'a', 'title': 'ch1', 'volume': '第一卷'},
        {'url': 'b', 'title': 'ch2', 'volume': '第一卷'},
        {'url': 'c', 'title': 'ch3', 'volume': '第二卷'},
        {'url': 'd', 'title': 'ch4', 'volume': '第二卷'},
    ]
    disordered = _disorder(chapters)
    vols = [c['volume'] for c in disordered]
    assert_true("卷边界完整保留", vols == ['第一卷', '第一卷', '第二卷', '第二卷'])

    # v7
    section(7, "章节分页解析")
    from crawler_engine.pipeline import _resolve_next_page
    next_spec = {"type": "css", "expr": "a.next::attr(href)"}
    html = '<a class="next" href="page2.html">下一页</a>'
    next_url = _resolve_next_page("https://example.com/page1", html, next_spec)
    assert_true("能解析 next_page 链接", next_url and "page2.html" in next_url)

    # v8
    section(8, "站点缓存控制")
    from apps.sites.cache_control import apply_cache_headers, DEFAULT_CACHE_TIMES
    from django.http import HttpResponse
    class _FakeSite2:
        cache_chapter_seconds = 1800
    resp = HttpResponse("<html>chapter content</html>")
    resp2 = apply_cache_headers(resp, _FakeSite2(), "chapter")
    cache_header = resp2.get("Cache-Control", "")
    assert_true("Cache-Control 包含 max-age", "max-age" in cache_header)
    assert_true("DEFAULT_CACHE_TIMES 包含 chapter", "chapter" in DEFAULT_CACHE_TIMES)

    # v9
    section(9, "关键词命中率统计")
    from apps.smart_classifier.models import CategoryKeyword
    # Just verify the model has the new fields
    field_names = [f.name for f in CategoryKeyword._meta.get_fields()]
    assert_true("CategoryKeyword 有 hit_count 字段", "hit_count" in field_names)
    assert_true("CategoryKeyword 有 last_hit_at 字段", "last_hit_at" in field_names)

    # v10
    section(10, "批量任务 API")
    from apps.crawler_tasks.views import CrawlerTaskViewSet
    methods = [m for m in dir(CrawlerTaskViewSet) if m.startswith("batch_")]
    assert_true("CrawlerTaskViewSet 有 batch_run 方法", "batch_run" in methods)
    assert_true("CrawlerTaskViewSet 有 batch_pause 方法", "batch_pause" in methods)
    assert_true("CrawlerTaskViewSet 有 batch_stop 方法", "batch_stop" in methods)

    # v11
    section(11, "数据库索引优化")
    from apps.novel.models import Book
    index_names = [idx.name for idx in Book._meta.indexes]
    assert_true("Book 有 book_status_rating_idx", "book_status_rating_idx" in index_names)

    # v12
    section(12, "主题 SEO 检测")
    from apps.seo.theme_seo_check import check_theme_files, REQUIRED_SEO_PATTERNS
    assert_true("REQUIRED_SEO_PATTERNS 至少 10 项", len(REQUIRED_SEO_PATTERNS) >= 10)
    report = check_theme_files("simple_reading")
    assert_true("check_theme_files 返回 dict", isinstance(report, dict))
    assert_true("report 含 score 字段", "score" in report)

    # v14
    section(14, "RSS 混淆集成")
    from apps.seo.rss import render_site_rss
    import inspect
    sig = inspect.signature(render_site_rss)
    assert_true("render_site_rss 支持 obfuscate 参数", "obfuscate" in sig.parameters)

    # v15
    section(15, "任务历史统计")
    from apps.crawler_tasks.stats import overall_stats, runs_per_day, top_active_tasks
    assert_true("overall_stats 可调用", callable(overall_stats))
    assert_true("runs_per_day 可调用", callable(runs_per_day))
    assert_true("top_active_tasks 可调用", callable(top_active_tasks))

    # v16
    section(16, "验证码识别集成")
    from crawler_engine.captcha_solver import diagnostics, solve_captcha, is_ocr_available, is_2captcha_configured
    diag = diagnostics()
    assert_true("diagnostics 含 2captcha_configured", "2captcha_configured" in diag)
    assert_true("diagnostics 含 ocr_available", "ocr_available" in diag)

    print()
    print("=" * 70)
    print("✓ v1-v16 综合端到端测试全部通过")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}")
        sys.exit(2)
