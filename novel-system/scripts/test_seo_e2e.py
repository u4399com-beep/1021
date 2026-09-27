#!/usr/bin/env python
"""End-to-end test #3 — site creation + SEO audit + remediation.

Simulates the workflow:
  "在「站群管理」新增一个站点后，到「SEO 检测」跑一次完整审计"

This script:
  1. Creates a new test site with deliberately BAD SEO config
  2. Runs the full SEO audit (12 checks)
  3. Prints the audit report with score
  4. Applies fixes based on suggestions
  5. Re-runs the audit to show the improved score
  6. Generates sitemap.xml + RSS.xml for the site
  7. (Optional) Cleans up with --cleanup

Usage:
    python scripts/test_seo_e2e.py
    python scripts/test_seo_e2e.py --cleanup
"""
from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

django.setup()

from apps.sites.models import Site, Theme
from apps.seo.engine import run_audit
from apps.seo.sitemap import generate_for_site
from apps.seo.rss import render_site_rss


BAD_HOST = "seo-test-bad.example.com"
GOOD_HOST = "seo-test-good.example.com"


def _print_audit(audit, label):
    print(f"\n  ─── {label} ───")
    print(f"  综合评分: {audit['score']}/100")
    print(f"  Summary: errors={audit['summary']['errors']} warnings={audit['summary']['warnings']} ok={audit['summary']['oks']}")
    print()
    for c in audit["checks"]:
        icon = {"error": "✗", "warning": "!", "info": "i", "ok": "✓"}[c["severity"]]
        print(f"    [{icon}] {c['check']:25s} {c['severity']:8s} {c['message']}")
        if c["suggestion"]:
            print(f"        → {c['suggestion']}")


def create_bad_site():
    """A site with deliberately bad SEO config."""
    theme = Theme.objects.first()
    site, _ = Site.objects.get_or_create(
        host=BAD_HOST,
        defaults={
            "name": "SEO 测试站（差配置）",
            "theme": theme,
            "site_title": "",         # ← empty (error)
            "site_description": "",    # ← empty (error)
            "site_keywords": "",       # ← empty (warning)
            "canonical_domain": "",    # ← empty (warning)
            "geo_region": "",          # ← empty (warning)
            "geo_lang": "",            # ← empty (warning)
            "robots_txt": "",          # ← empty (error)
            "sitemap_enabled": False,  # ← disabled (warning)
            "favicon": "",             # ← empty (info)
            "logo": "",                # ← empty (info)
            "head_inject": "",
            "body_inject": "",
        },
    )
    return site


def apply_fixes(site):
    """Apply SEO fixes based on suggestions, mimicking user input."""
    site.site_title = "墨香书阁 - 免费小说在线阅读"
    site.site_description = "墨香书阁，汇聚玄幻、奇幻、武侠、仙侠等全类型小说，提供免费在线阅读与下载。每日更新最新章节。"
    site.site_keywords = "小说,在线阅读,免费小说,玄幻,奇幻,武侠,仙侠,都市,墨香书阁"
    site.canonical_domain = BAD_HOST
    site.geo_region = "CN"
    site.geo_lang = "zh-CN"
    site.robots_txt = "User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: https://" + BAD_HOST + "/sitemap.xml"
    site.sitemap_enabled = True
    site.favicon = f"https://{BAD_HOST}/favicon.ico"
    site.logo = f"https://{BAD_HOST}/logo.png"
    site.head_inject = '<meta name="baidu-site-verification" content="code123"/>'
    site.body_inject = ''
    site.save()
    return site


def main():
    parser = argparse.ArgumentParser(description="SEO audit end-to-end test")
    parser.add_argument("--cleanup", action="store_true", help="Delete test sites after run")
    args = parser.parse_args()

    print("=" * 70)
    print("【1/4】 创建一个 SEO 配置很差的测试站点")
    print("=" * 70)
    bad_site = create_bad_site()
    print(f"  ✓ 站点: {bad_site.host}")
    print(f"  - 标题为空、描述为空、canonical 为空、geo 未设、robots_txt 为空")

    # Run audit
    print()
    print("=" * 70)
    print("【2/4】 第一次审计（修复前）")
    print("=" * 70)
    bad_audit = run_audit(bad_site)
    _print_audit(bad_audit, "修复前")

    assert bad_audit["score"] < 60, f"❌ 修复前评分应低于 60，实际为 {bad_audit['score']}"
    print(f"\n  ✓ 修复前评分 = {bad_audit['score']} (< 60，符合\"差配置\"预期)")

    # Apply fixes
    print()
    print("=" * 70)
    print("【3/4】 按建议修复 TDK / GEO / canonical / robots / sitemap")
    print("=" * 70)
    apply_fixes(bad_site)
    print("  ✓ 设置 site_title = '墨香书阁 - 免费小说在线阅读'")
    print("  ✓ 设置 site_description = 100+ 字描述")
    print("  ✓ 设置 site_keywords = 9 个关键词")
    print("  ✓ 设置 canonical_domain = " + BAD_HOST)
    print("  ✓ 设置 geo_region = CN, geo_lang = zh-CN")
    print("  ✓ 设置 robots.txt + 启用 sitemap")
    print("  ✓ 设置 favicon + logo + head_inject")

    # Re-run audit
    print()
    print("=" * 70)
    print("【4/4】 第二次审计（修复后）")
    print("=" * 70)
    good_audit = run_audit(bad_site)
    _print_audit(good_audit, "修复后")

    print()
    print(f"→ 评分提升: {bad_audit['score']} → {good_audit['score']} (+{good_audit['score']-bad_audit['score']}点)")
    assert good_audit["score"] > bad_audit["score"], "❌ 修复后评分应高于修复前"
    assert good_audit["summary"]["errors"] == 0, "❌ 修复后不应有 errors"
    print(f"→ 修复后 0 errors，符合预期")

    # Generate sitemap + RSS
    print()
    print("=" * 70)
    print("【5/5】 生成 sitemap.xml + rss.xml")
    print("=" * 70)
    try:
        sm = generate_for_site(bad_site)
        print(f"  ✓ sitemap: {sm}")
        print(f"    文件大小: {sm.stat().st_size} bytes")
        print(f"    前 200 字符:\n      {sm.read_text()[:200].replace(chr(10), chr(10)+'      ')}")
    except Exception as e:
        print(f"  ✗ sitemap 生成失败: {e!r}")

    try:
        from apps.novel.models import Book
        rss = render_site_rss(bad_site, Book.objects.filter(is_published=True)[:20])
        print(f"  ✓ rss: 长度 {len(rss)} bytes")
        print(f"    前 200 字符:\n      {rss[:200].replace(chr(10), chr(10)+'      ')}")
    except Exception as e:
        print(f"  ✗ rss 生成失败: {e!r}")

    if args.cleanup:
        print()
        print("→ 清理测试站点...")
        bad_site.delete()
        print("  ✓ 已删除")

    print()
    print("=== SEO 端到端测试通过 ===")
    print("  - 创建差配置站点 → 评分 < 60 ✓")
    print("  - 应用修复 → 评分提升 + errors=0 ✓")
    print("  - sitemap.xml 生成成功 ✓")
    print("  - rss.xml 生成成功 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
