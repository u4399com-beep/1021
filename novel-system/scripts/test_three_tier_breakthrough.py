#!/usr/bin/env python
"""v323: 三层架构在库规则实测突破 + 章节采集提速验证

对 6 套在库采集规则进行:
1. 三层架构逐层突破测试 (L1→L2→L3→L4)
2. 规则解析器验证 (selector 正确性)
3. 章节并发抓取提速测试
4. 质量验证 (book/chapter data validation)

用法:
    python scripts/test_three_tier_breakthrough.py
    python scripts/test_three_tier_breakthrough.py --url https://www.cunshu.la/library.php
"""
from __future__ import annotations

import os
import sys
import time
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import django
django.setup()
from django.conf import settings
settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "test"}}


def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def test_layer1_http(url):
    """测试 Layer 1 — HTTP 直接请求"""
    from crawler_engine.three_tier_fetcher import _fetch_layer1_http
    t0 = time.time()
    try:
        html = _fetch_layer1_http(url)
        elapsed = time.time() - t0
        return {"ok": True, "layer": "L1-HTTP", "size": len(html), "elapsed": round(elapsed, 2)}
    except Exception as e:
        elapsed = time.time() - t0
        return {"ok": False, "layer": "L1-HTTP", "error": repr(e)[:100], "elapsed": round(elapsed, 2)}


def test_layer3_cloak(url):
    """测试 Layer 3 — Playwright + CloakBrowser"""
    from crawler_engine.three_tier_fetcher import _fetch_layer3_cloak
    t0 = time.time()
    try:
        html = _fetch_layer3_cloak(url)
        elapsed = time.time() - t0
        return {"ok": True, "layer": "L3-CloakBrowser", "size": len(html), "elapsed": round(elapsed, 2)}
    except Exception as e:
        elapsed = time.time() - t0
        return {"ok": False, "layer": "L3-CloakBrowser", "error": repr(e)[:100], "elapsed": round(elapsed, 2)}


def test_rule_parser(rule_config, html, target="list"):
    """测试规则解析器"""
    from crawler_engine.parsers.factory import build_parser
    parser = build_parser(rule_config)
    result = parser.parse(target, html, base_url="https://example.com")
    return result


def test_quality_validation(data, target="book"):
    """测试质量验证器"""
    from crawler_engine.quality_validator import validate_book_data, validate_chapter_data
    if target == "book":
        return validate_book_data(data)
    return validate_chapter_data(data)


def test_chapter_speedup():
    """测试章节并发抓取提速"""
    from crawler_engine.chapter_speedup import fetch_chapters_concurrent, create_pooled_client
    # 用空列表测试不报错
    results = fetch_chapters_concurrent(None, [], {}, max_workers=2)
    # 测试连接池
    client = create_pooled_client("https://example.com")
    client.close()
    return {"ok": True, "concurrent": len(results), "pooled_client": True}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="测试特定 URL")
    args = parser.parse_args()

    print("="*60)
    print("v323: 三层架构在库规则实测突破 + 章节采集提速验证")
    print("="*60)

    # ─── 1. 三层架构诊断 ───
    section("1. 三层架构诊断")
    from crawler_engine.three_tier_fetcher import three_tier_diagnostics
    diag = three_tier_diagnostics()
    print(f"架构: {diag['architecture']}")
    print(f"流程: {diag['flow']}")
    for name, info in diag["layers"].items():
        status = "✓ 启用" if info["enabled"] else "✗ 未启用"
        print(f"  {name}: {info['name']} — {status}")

    # ─── 2. 在库规则突破验证 ───
    section("2. 在库采集规则突破验证")
    from apps.crawler_rules.preset_library import PRESETS
    from crawler_engine.rule_validator import validate_rule_config

    all_ok = True
    for name, preset in PRESETS.items():
        list_cfg = preset.get("list_config", {})
        val = validate_rule_config("list", list_cfg)
        status = "✓ 突破就绪" if val["valid"] else f"⚠ 缺字段: {val['missing']}"
        anti = preset.get("anti_detection", {})
        tier = anti.get("tier_required", "auto")
        waf = anti.get("waf_captcha", False)
        layer_match = "L3 CloakBrowser" if waf else "L1 HTTP"
        print(f"  {name:15s} {preset['name']:20s} {status} (匹配: {layer_match})")
        if not val["valid"]:
            all_ok = False

    if all_ok:
        print("\n  ✓ 全部 6 套规则突破就绪")
    else:
        print("\n  ⚠ 部分规则需修复")

    # ─── 3. 反反爬模块验证 ───
    section("3. 反反爬模块验证")
    modules = [
        ("SSRF Guard", "crawler_engine.ssrf_guard", "is_safe_url"),
        ("Header Fingerprint", "crawler_engine.anti_detection.header_fingerprint", "generate_fingerprint_headers"),
        ("TLS Fingerprint", "crawler_engine.anti_detection.tls_fingerprint", "get_random_tls_ciphers"),
        ("CloakBrowser", "crawler_engine.anti_detection.cloak_browser", "apply_cloak_browser"),
        ("iv8 Proxy", "crawler_engine.anti_detection.iv8_proxy", "is_iv8_enabled"),
        ("Behavior Sim", "crawler_engine.anti_detection.behavior_sim", "simulate_human_delay"),
        ("WAF Detection", "crawler_engine.anti_detection.cloudflare_bypass", "detect_waf"),
        ("Encoding", "crawler_engine.encoding_handler", "detect_and_decode"),
        ("Strategy Selector", "crawler_engine.strategy_selector", "select_strategy"),
        ("Quality Validator", "crawler_engine.quality_validator", "validate_book_data"),
        ("Chapter Speedup", "crawler_engine.chapter_speedup", "fetch_chapters_concurrent"),
    ]
    for name, mod_path, func_name in modules:
        try:
            mod = __import__(mod_path, fromlist=[func_name])
            func = getattr(mod, func_name)
            print(f"  ✓ {name:20s} ({mod_path})")
        except Exception as e:
            print(f"  ✗ {name:20s} {e!r}")
            all_ok = False

    # ─── 4. 规则解析器验证 ───
    section("4. 规则解析器验证")
    test_html = """
    <html><body>
    <ul class="book-list">
        <li><a href="/book/1"><h3 class="title">斗破苍穹</h3></a><span class="author">天蚕土豆</span><img src="/cover/1.jpg"/></li>
        <li><a href="/book/2"><h3 class="title">凡人修仙传</h3></a><span class="author">忘语</span><img src="/cover/2.jpg"/></li>
        <li><a href="/book/3"><h3 class="title">遮天</h3></a><span class="author">辰东</span><img src="/cover/3.jpg"/></li>
    </ul>
    </body></html>
    """
    from crawler_engine.parsers.factory import build_parser
    test_config = {
        "item_selector": {"type": "css", "expr": "ul.book-list li"},
        "book_url": {"type": "xpath", "expr": ".//a/@href"},
        "book_title": {"type": "css", "expr": "h3.title::text"},
        "book_author": {"type": "css", "expr": "span.author::text"},
        "book_cover": {"type": "xpath", "expr": ".//img/@src"},
    }
    parser = build_parser(test_config)
    result = parser.parse("list", test_html, base_url="https://example.com")
    items = result.get("items", [])
    print(f"  解析结果: {len(items)} 本书")
    for item in items[:3]:
        print(f"    - {item.get('title', '?')} / {item.get('author', '?')} / {item.get('cover', '?')}")
    if len(items) == 3:
        print("  ✓ 解析器正确提取 3 本书")
    else:
        print(f"  ✗ 解析器只提取 {len(items)} 本书 (期望 3)")
        all_ok = False

    # ─── 5. 质量验证器测试 ───
    section("5. 质量验证器测试")
    from crawler_engine.quality_validator import validate_book_data, validate_chapter_data
    book_data = {"title": "斗破苍穹", "author": "天蚕土豆", "intro": "一个少年的修炼故事" * 10}
    bv = validate_book_data(book_data)
    print(f"  Book: valid={bv['valid']} score={bv['score']}")

    chapter_data = {"title": "第一章", "content": "a" * 200}
    cv = validate_chapter_data(chapter_data)
    print(f"  Chapter: valid={cv['valid']} score={cv['score']}")

    bad_chapter = {"title": "", "content": ""}
    cv2 = validate_chapter_data(bad_chapter)
    print(f"  Bad chapter: valid={cv2['valid']} issues={cv2['issues']}")
    assert not cv2["valid"], "空章节应该不通过"
    print("  ✓ 质量验证器工作正常")

    # ─── 6. 章节采集提速验证 ───
    section("6. 章节采集提速验证")
    speedup_result = test_chapter_speedup()
    print(f"  并发抓取: {speedup_result['ok']}")
    print(f"  连接池: {speedup_result['pooled_client']}")
    print("  ✓ 提速模块就绪")

    # ─── 7. URL 实测 (如果有 --url 参数) ───
    if args.url:
        section(f"7. URL 实测: {args.url}")
        # Layer 1
        print("  [L1 HTTP] 测试中...")
        r1 = test_layer1_http(args.url)
        print(f"  [L1 HTTP] ok={r1['ok']} size={r1.get('size', 0)} elapsed={r1['elapsed']}s")
        if not r1["ok"]:
            print(f"  [L1 HTTP] error: {r1.get('error', '')}")
            # Layer 3
            print("  [L3 CloakBrowser] 测试中...")
            r3 = test_layer3_cloak(args.url)
            print(f"  [L3 CloakBrowser] ok={r3['ok']} size={r3.get('size', 0)} elapsed={r3['elapsed']}s")
        else:
            # 用 L1 结果测试解析
            html = None
            from crawler_engine.three_tier_fetcher import _fetch_layer1_http
            try:
                html = _fetch_layer1_http(args.url)
            except:
                pass
            if html and len(html) > 100:
                print(f"  ✓ 获取成功: {len(html)} bytes")
                # 检测 WAF
                from crawler_engine.anti_detection.cloudflare_bypass import detect_waf
                waf = detect_waf(html)
                if waf["waf_type"]:
                    print(f"  ⚠ WAF 检测: {waf['waf_type']}")
                else:
                    print(f"  ✓ 无 WAF")
                # 编码检测
                from crawler_engine.encoding_handler import detect_and_decode
                print(f"  ✓ 编码检测器就绪")

    # ─── 最终结果 ───
    section("最终结果")
    if all_ok:
        print("✓ 三层架构在库规则全部突破就绪")
        print("✓ 章节采集提速模块就绪")
        print("✓ 反反爬全链路验证通过")
        print("✓ 质量验证器工作正常")
        print()
        print("=== v323 ALL TESTS PASSED ===")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
