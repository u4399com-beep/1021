#!/usr/bin/env python
"""End-to-end test #1 — Crawler engine tier testing.

Simulates the workflow the user described:
  "在「系统设置 → 采集引擎」面板填入 API Key + 测试 URL"

Without needing a browser, this script:
  1. Reads API keys from environment (.env)
  2. Reports each tier's status
  3. Tests a URL with each available tier
  4. Prints a tabulated report

Usage:
    # Test all tiers in fallback order
    python scripts/test_engine_e2e.py https://example.com/list

    # Test only one tier
    python scripts/test_engine_e2e.py https://example.com/list --tier firecrawl

    # Test all tiers individually (even after one succeeds)
    python scripts/test_engine_e2e.py https://example.com/list --all
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


def main():
    parser = argparse.ArgumentParser(description="Test crawler engine tiers end-to-end.")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--tier", choices=["httpx", "firecrawl", "browser-use", "playwright"],
                        help="Test only this tier")
    parser.add_argument("--all", action="store_true",
                        help="Test all tiers individually, even after one succeeds")
    args = parser.parse_args()

    from crawler_engine.fetcher import diagnose, test_url
    from crawler_engine.anti_detection.pool import hyperbrowser_diagnostics

    # ── Section 1: Tier status ───────────────────────────────
    print("=" * 70)
    print("【1/3】 采集引擎 Tier 状态")
    print("=" * 70)
    diag = diagnose()
    headers = ["Tier", "Installed", "Configured", "Note"]
    rows = []
    for name, info in diag.items():
        notes = []
        if info.get("hyperbrowser"):
            notes.append("hyperbrowser=on")
        if not info.get("installed"):
            notes.append("未安装 pip 包")
        elif not info.get("configured"):
            notes.append("缺少 API Key")
        rows.append([
            name,
            "✓" if info.get("installed") else "✗",
            "✓" if info.get("configured") else "✗",
            ", ".join(notes) or "ready",
        ])

    col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
    fmt = "  ".join([f"{{:<{w}}}" for w in col_widths])
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in col_widths]))
    for r in rows:
        print(fmt.format(*r))

    # ── Section 2: Hyperbrowser sessions ───────────────────
    print()
    print("=" * 70)
    print("【2/3】 Hyperbrowser 代理池状态")
    print("=" * 70)
    hb = hyperbrowser_diagnostics()
    if hb["configured"]:
        print(f"  API Key: 已配置")
        print(f"  活跃会话数: {hb['active_sessions']}")
        for s in hb["sessions"]:
            print(f"    - session={s['session_id']} region={s['region']} expires_in={s['expires_in_seconds']}s")
    else:
        print(f"  API Key: 未配置（HYPERBROWSER_API_KEY 为空）")
        print(f"  跳过 Hyperbrowser 实测，但 Playwright 仍可本地运行")

    # ── Section 3: Test URL ────────────────────────────────
    print()
    print("=" * 70)
    print(f"【3/3】 实测 URL: {args.url}")
    print("=" * 70)

    target_tier = args.tier
    if target_tier:
        result = test_url(args.url, tier=target_tier)
        _print_results([result], args.url)
        return 0 if any(r.get("success") for r in result.get("results", [])) else 2

    # Fallback order (default behavior)
    if not args.all:
        result = test_url(args.url, tier=None)
        _print_results([result], args.url)
        return 0 if any(r.get("success") for r in result.get("results", [])) else 2

    # All tiers individually
    print("\n[所有 Tier 逐个测试]\n")
    all_results = []
    for tier_name in ["httpx", "firecrawl", "browser-use", "playwright"]:
        r = test_url(args.url, tier=tier_name)
        all_results.append(r)
    _print_results(all_results, args.url)
    return 0 if any(r.get("success") for r in [r for res in all_results for r in res.get("results", [])]) else 2


def _print_results(results_list, url):
    for r in results_list:
        for res in r.get("results", []):
            tier = res["tier"]
            ok = res["success"]
            elapsed = res["elapsed_ms"]
            size = res["html_size"]
            err = res.get("error") or ""
            icon = "✓" if ok else "✗"
            print(f"  {icon} {tier:14s}  {elapsed:5d}ms  size={size:7d}  err={err[:60]}")
    print()
    # Overall
    all_ok = any(
        r.get("success")
        for res in results_list
        for r in res.get("results", [])
    )
    print("→ 结果: " + ("至少一个 Tier 成功" if all_ok else "全部失败"))


if __name__ == "__main__":
    sys.exit(main())
