"""HTTP + iv8 + CloakBrowser 三层架构集成 (v319)

架构设计:
  Layer 1 (HTTP):    httpx + 随机 UA/Header/TLS → 快速获取 (90% 站点)
  Layer 2 (iv8):     httpx + iv8 住宅 IP 代理 → 绕过 IP 封禁
  Layer 3 (CloakBrowser): Playwright + 6 层指纹隐藏 → 最难反爬站点
  Layer 4 (AI):      Firecrawl/BrowserUse → 兜底

每层独立工作，上层失败自动降级到下层。
Layer 1 和 Layer 2 都用 httpx，区别在于 Layer 2 加入 iv8 代理。
Layer 3 用 Playwright + CloakBrowser + Stealth + 行为模拟。

配置 (.env):
    # iv8 代理
    IV8_API_KEY=your-key
    # 三层架构总开关
    CRAWLER_THREE_TIER_ENABLED=true
"""
from __future__ import annotations

import random
import time
from typing import Optional
from loguru import logger


# ─── 三层架构配置 ─────────────────────────────────────────
THREE_TIER_CONFIG = {
    "layer1_http": {
        "name": "HTTP 直接请求",
        "timeout": 15,
        "max_redirects": 5,
        "description": "httpx + 随机 UA/Header/TLS → 最快，90% 站点可直接获取",
    },
    "layer2_iv8": {
        "name": "HTTP + iv8 代理",
        "timeout": 20,
        "max_redirects": 5,
        "description": "httpx + iv8 住宅 IP 轮换 + TLS 指纹 → 绕过 IP 封禁",
    },
    "layer3_cloak": {
        "name": "Playwright + CloakBrowser",
        "timeout": 30,
        "description": "完整浏览器 + 6 层指纹隐藏 + 行为模拟 → 最难反爬站点",
    },
}


def fetch_three_tier(url: str, *, use_browser: bool = False) -> str:
    """三层架构抓取 — 逐层降级直到成功。

    Args:
        url: 目标 URL
        use_browser: True = 跳过 Layer 1-2，直接用 Layer 3

    Returns: HTML 字符串

    Raises: RuntimeError 如果所有层都失败
    """
    from .ssrf_guard import is_safe_url
    if not is_safe_url(url):
        raise ValueError(f"SSRF blocked: {url}")

    errors = []

    # ─── Layer 1: HTTP 直接请求 ───────────────────────────
    if not use_browser:
        try:
            html = _fetch_layer1_http(url)
            logger.info(f"Layer1 (HTTP) OK: {url[:60]} len={len(html)}")
            return html
        except Exception as e:
            errors.append(f"L1: {e!r}")
            logger.info(f"Layer1 (HTTP) failed: {e!r} → 降级到 Layer2")

    # ─── Layer 2: HTTP + iv8 代理 ─────────────────────────
    if not use_browser:
        try:
            html = _fetch_layer2_iv8(url)
            logger.info(f"Layer2 (iv8) OK: {url[:60]} len={len(html)}")
            return html
        except Exception as e:
            errors.append(f"L2: {e!r}")
            logger.info(f"Layer2 (iv8) failed: {e!r} → 降级到 Layer3")

    # ─── Layer 3: Playwright + CloakBrowser ──────────────
    try:
        html = _fetch_layer3_cloak(url)
        logger.info(f"Layer3 (CloakBrowser) OK: {url[:60]} len={len(html)}")
        return html
    except Exception as e:
        errors.append(f"L3: {e!r}")
        logger.warning(f"Layer3 (CloakBrowser) failed: {e!r}")

    # ─── Layer 4: AI 兜底 (Firecrawl/BrowserUse) ─────────
    try:
        html = _fetch_layer4_ai(url)
        if html:
            logger.info(f"Layer4 (AI) OK: {url[:60]} len={len(html)}")
            return html
    except Exception as e:
        errors.append(f"L4: {e!r}")

    raise RuntimeError(f"所有层失败: {'; '.join(errors)}")


# ─── Layer 1: HTTP 直接请求 ─────────────────────────────
def _fetch_layer1_http(url: str) -> str:
    """Layer 1 — httpx + 随机 UA/Header/编码检测。"""
    import httpx
    from .anti_detection.header_fingerprint import generate_fingerprint_headers, get_random_referer, get_random_dnt, reorder_headers

    headers = generate_fingerprint_headers()
    # Referer
    ref = get_random_referer()
    if ref:
        headers["Referer"] = ref
    # DNT
    dnt = get_random_dnt()
    if dnt:
        headers["DNT"] = dnt
    # Header 顺序随机化
    headers = reorder_headers(headers)

    with httpx.Client(timeout=15, follow_redirects=True, max_redirects=5) as client:
        r = client.get(url, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}")
        # 编码检测
        from .encoding_handler import detect_and_decode
        return detect_and_decode(r.content, r.headers.get("content-type", ""))


# ─── Layer 2: HTTP + iv8 代理 ───────────────────────────
def _fetch_layer2_iv8(url: str) -> str:
    """Layer 2 — httpx + iv8 住宅 IP 代理 + 随机 UA/Header。"""
    from .anti_detection.iv8_proxy import is_iv8_enabled, get_proxy

    if not is_iv8_enabled():
        raise RuntimeError("iv8 not configured")

    proxy_url = get_proxy()
    if not proxy_url:
        raise RuntimeError("no iv8 proxy available")

    import httpx
    from .anti_detection.header_fingerprint import generate_fingerprint_headers, reorder_headers

    headers = reorder_headers(generate_fingerprint_headers())

    with httpx.Client(
        timeout=20, follow_redirects=True, max_redirects=5,
        proxy=proxy_url,
    ) as client:
        r = client.get(url, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} via iv8")
        from .encoding_handler import detect_and_decode
        return detect_and_decode(r.content, r.headers.get("content-type", ""))


# ─── Layer 3: Playwright + CloakBrowser ─────────────────
def _fetch_layer3_cloak(url: str) -> str:
    """Layer 3 — Playwright + Stealth + CloakBrowser + 行为模拟 + iv8 代理。"""
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
    except ImportError:
        raise RuntimeError("playwright not installed")

    from .anti_detection.header_fingerprint import get_random_fingerprint
    from .anti_detection.cloak_browser import apply_cloak_browser
    from .anti_detection.behavior_sim import full_human_simulation
    from .anti_detection.cloudflare_bypass import detect_waf
    from .anti_detection.iv8_proxy import is_iv8_enabled, get_proxy_for_playwright

    # 检查 WAF
    # (WAF 检测需要先 fetch 一次，这里直接用 Playwright 让浏览器处理)

    fp = get_random_fingerprint()

    with sync_playwright() as p:
        # iv8 代理（如果启用）
        launch_args = ["--no-sandbox", "--disable-dev-shm-usage",
                       "--disable-blink-features=AutomationControlled"]

        if is_iv8_enabled():
            iv8_proxy = get_proxy_for_playwright()
            if iv8_proxy:
                browser = p.chromium.launch(
                    headless=True,
                    args=launch_args,
                    proxy=iv8_proxy,
                )
                logger.info(f"Layer3: iv8 proxy {iv8_proxy['server'][:30]}")
            else:
                browser = p.chromium.launch(headless=True, args=launch_args)
        else:
            browser = p.chromium.launch(headless=True, args=launch_args)

        context = browser.new_context(
            user_agent=fp.get("user_agent", "Mozilla/5.0"),
            viewport=fp["viewport"],
            locale=fp["locale"],
            timezone_id=fp["timezone_id"],
            extra_http_headers=fp["extra_http_headers"],
        )

        page = context.new_page()
        # 标准 Stealth
        try:
            Stealth().apply(page)
        except Exception:
            pass

        # CloakBrowser 深度指纹隐藏 (6 层)
        try:
            apply_cloak_browser(page)
        except Exception:
            pass

        # 页面加载
        page.goto(url, wait_until="domcontentloaded", timeout=30 * 1000)
        page.wait_for_timeout(2000)

        # 行为模拟
        try:
            full_human_simulation(page)
        except Exception:
            pass

        # WAF 验证码自动解决
        try:
            from .playwright_client import _detect_captcha, _try_solve_captcha
            for _ in range(3):
                if not _detect_captcha(page):
                    break
                _try_solve_captcha(page)
                page.wait_for_timeout(3000)
        except Exception:
            pass

        html = page.content()
        browser.close()
        return html


# ─── Layer 4: AI 兜底 ───────────────────────────────────
def _fetch_layer4_ai(url: str) -> Optional[str]:
    """Layer 4 — Firecrawl 或 BrowserUse AI 托管。"""
    # 尝试 Firecrawl
    try:
        from .firecrawl_client import is_enabled as firecrawl_enabled, scrape_html as firecrawl_scrape
        if firecrawl_enabled():
            return firecrawl_scrape(url)
    except Exception:
        pass

    # 尝试 BrowserUse
    try:
        from .browser_use_client import is_enabled as bu_enabled, scrape_html as bu_scrape
        if bu_enabled():
            return bu_scrape(url)
    except Exception:
        pass

    return None


def three_tier_diagnostics() -> dict:
    """返回三层架构配置和状态。"""
    from .anti_detection.iv8_proxy import is_iv8_enabled

    return {
        "architecture": "HTTP + iv8 + CloakBrowser (3-tier)",
        "layers": {
            "layer1_http": {
                "name": THREE_TIER_CONFIG["layer1_http"]["name"],
                "enabled": True,
            },
            "layer2_iv8": {
                "name": THREE_TIER_CONFIG["layer2_iv8"]["name"],
                "enabled": is_iv8_enabled(),
            },
            "layer3_cloak": {
                "name": THREE_TIER_CONFIG["layer3_cloak"]["name"],
                "enabled": True,
                "scripts": 6,  # WebGL + Canvas + Audio + Navigator + Screen + Font
            },
            "layer4_ai": {
                "name": "Firecrawl/BrowserUse (AI fallback)",
                "enabled": True,
            },
        },
        "flow": "L1(HTTP) → L2(iv8) → L3(CloakBrowser) → L4(AI)",
    }
