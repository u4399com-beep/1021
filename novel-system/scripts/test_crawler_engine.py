#!/usr/bin/env python
"""Quick test for the three-tier fetch fallback chain.

Usage:
    # Test all tiers against a URL (the chain stops at the first success)
    python scripts/test_crawler_engine.py https://example.com/list

    # Test a specific tier only
    python scripts/test_crawler_engine.py https://example.com/list --tier firecrawl

    # Show tier status without testing
    python scripts/test_crawler_engine.py --status
"""
from __future__ import annotations

import argparse
import os
import sys

# Bootstrap Django so we can use settings.CRAWLER config
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django  # noqa: E402

# Make sure backend/ is on sys.path so `apps.*` and `crawler_engine.*` import
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

django.setup()

from crawler_engine.fetcher import diagnose, test_url  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Test crawler engine tiers.")
    parser.add_argument("url", nargs="?", help="URL to fetch")
    parser.add_argument("--tier", choices=["httpx", "firecrawl", "browser-use", "playwright"],
                        help="Test only this tier")
    parser.add_argument("--status", action="store_true", help="Show tier status only")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.status:
        diag = diagnose()
        if args.json:
            import json
            print(json.dumps(diag, indent=2, ensure_ascii=False))
        else:
            print("=== Crawler Engine Status ===")
            for tier, info in diag.items():
                print(f"  {tier:14s} installed={info.get('installed')} "
                      f"configured={info.get('configured')} "
                      f"hyperbrowser={info.get('hyperbrowser', '-')}")
        return 0

    if not args.url:
        parser.print_help()
        return 1

    print(f"Testing URL: {args.url}")
    print(f"Target tier: {args.tier or 'auto (fallback chain)'}")
    print("-" * 70)

    result = test_url(args.url, tier=args.tier)
    if args.json:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        for r in result.get("results", []):
            tag = "✓" if r["success"] else "✗"
            print(f"  {tag} {r['tier']:14s} elapsed={r['elapsed_ms']}ms html_size={r['html_size']} err={r['error']}")

    # Exit 0 if at least one tier succeeded
    success_any = any(r.get("success") for r in result.get("results", []))
    return 0 if success_any else 2


if __name__ == "__main__":
    sys.exit(main())
