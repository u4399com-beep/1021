#!/usr/bin/env python
"""End-to-end test for the SEO audit engine.

Usage:
    python scripts/test_seo_engine.py

This script:
  1. Bootstraps Django
  2. Creates a sample Site record (if none exists)
  3. Runs the SEO audit
  4. Prints the audit report
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

from apps.sites.models import Site, Theme
from apps.seo.engine import run_audit, run_audit_all_sites
from apps.seo.sitemap import generate_for_site
from apps.seo.rss import render_site_rss


def ensure_site():
    if Site.objects.exists():
        return Site.objects.first()
    theme = Theme.objects.first()
    if not theme:
        print("ERROR: no themes seeded. Run `python manage.py init_default_data` first.")
        sys.exit(1)
    return Site.objects.create(
        host="test.example.com",
        name="测试站点",
        theme=theme,
        site_title="测试站点 - 免费小说阅读",
        site_description="测试站点的描述",
        site_keywords="小说,阅读,测试",
    )


def main():
    print("=== SEO Engine Test ===\n")

    site = ensure_site()
    print(f"Site: {site.host} ({site.name})\n")

    report = run_audit(site)
    print(f"综合评分: {report['score']}/100")
    print(f"Summary: errors={report['summary']['errors']} warnings={report['summary']['warnings']} ok={report['summary']['oks']}\n")
    print("Checks:")
    for c in report["checks"]:
        icon = {"error": "✗", "warning": "!", "info": "i", "ok": "✓"}[c["severity"]]
        print(f"  [{icon}] {c['check']:25s} {c['severity']:8s} {c['message']}")
        if c["suggestion"]:
            print(f"       → {c['suggestion']}")

    print("\n=== Generate Sitemap ===\n")
    try:
        path = generate_for_site(site)
        print(f"✓ Generated: {path}")
        print(f"  First 200 chars: {path.read_text()[:200]}...")
    except Exception as e:
        print(f"✗ Sitemap generation failed: {e!r}")

    print("\n=== Generate RSS ===\n")
    try:
        xml = render_site_rss(site, [])
        print(f"✓ RSS generated, length={len(xml)}")
        print(f"  First 200 chars: {xml[:200]}...")
    except Exception as e:
        print(f"✗ RSS generation failed: {e!r}")


if __name__ == "__main__":
    main()
