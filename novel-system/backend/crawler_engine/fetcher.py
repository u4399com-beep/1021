"""crawler_engine.fetcher — three-tier fetch with graceful fallback.

Tier 0 (cheap):  requests/httpx           — static pages, 90% of sites
Tier 1 (AI host): Firecrawl                — handles JS rendering + anti-bot
Tier 2 (LLM):    Browser Use              — flexible interaction, slow
Tier 3 (local):  Playwright + Stealth (+ Hyperbrowser optional)

The orchestrator walks tiers in order. A tier is skipped if:
  - Its package is not installed (RuntimeError → catch + log + next tier)
  - Its API key is not configured (same path)

For each enabled tier, up to `max_retries` attempts are made before moving on.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from loguru import logger

from .anti_detection.pool import get_cookie, get_proxy, get_user_agent


# ------------------------------------------------------------------
# Retry context
# ------------------------------------------------------------------
@dataclass
class FetchContext:
    url: str
    method: str = "GET"
    headers: dict | None = None
    timeout: int = 30
    use_browser: bool = False
    max_retries: int = 3
    proxy: Optional[str] = None
    raw_headers: bool = False


# ------------------------------------------------------------------
# Tier 0 — httpx (synchronous)
# ------------------------------------------------------------------
def fetch_with_httpx(ctx: FetchContext) -> str:
    import httpx

    try:
        from .anti_detection.header_fingerprint import generate_fingerprint_headers
        headers = generate_fingerprint_headers()
    except ImportError:
        headers = {
        "User-Agent": get_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    if ctx.headers:
        headers.update(ctx.headers)

    with httpx.Client(timeout=ctx.timeout, follow_redirects=True, max_redirects=5) as client:
        r = client.get(ctx.url, headers=headers)
        # v157: WAF detection
        if r.status_code == 403 or r.status_code == 429:
            from .anti_detection.cloudflare_bypass import detect_waf
            waf = detect_waf(r.text, dict(r.headers))
            if waf["waf_type"]:
                logger.warning(f"WAF detected: {waf["waf_type"]} url={ctx.url[:60]}")
        if r.status_code >= 400:
            raise RuntimeError(f"httpx: status {r.status_code}")
        # Detect encoding properly, fallback to utf-8
        try:
            from .encoding_handler import detect_and_decode
            return detect_and_decode(r.content, r.headers.get("content-type", ""))
        except ImportError:
            encoding = r.charset or r.encoding or "utf-8"
            return r.content.decode(encoding, errors="replace")


# ------------------------------------------------------------------
# Tier 1 — Firecrawl
# ------------------------------------------------------------------
def fetch_with_firecrawl(ctx: FetchContext) -> str:
    from .firecrawl_client import is_enabled, scrape_html

    if not is_enabled():
        raise RuntimeError("firecrawl: API key not configured")
    return scrape_html(ctx.url, wait_for=2000)


# ------------------------------------------------------------------
# Tier 2 — Browser Use
# ------------------------------------------------------------------
def fetch_with_browser_use(ctx: FetchContext) -> str:
    from .browser_use_client import is_enabled, scrape_html

    if not is_enabled():
        raise RuntimeError("browser-use: API key not configured")
    task_hint = "Return the raw HTML of the entire page body."
    return scrape_html(ctx.url, task_hint=task_hint)


# ------------------------------------------------------------------
# Tier 3 — Playwright + Stealth (+ optional Hyperbrowser)
# ------------------------------------------------------------------
def fetch_with_playwright(ctx: FetchContext) -> str:
    from .playwright_client import is_enabled, scrape_html

    if not is_enabled():
        raise RuntimeError("playwright: not installed")
    proxy = ctx.proxy or get_proxy()
    return scrape_html(
        ctx.url,
        use_browser=ctx.use_browser,
        proxy=proxy,
        timeout=ctx.timeout,
    )


# ------------------------------------------------------------------
# Orchestration
# ------------------------------------------------------------------
TIERS = (
    ("httpx",       fetch_with_httpx),
    ("firecrawl",   fetch_with_firecrawl),
    ("browser-use", fetch_with_browser_use),
    ("playwright",  fetch_with_playwright),
)


def _check_ssrf(url: str) -> None:
    """v124: Block SSRF in all fetch paths."""
    from .ssrf_guard import is_safe_url
    if not is_safe_url(url):
        raise ValueError(f"URL blocked by SSRF protection: {url}")


def fetch_page(url: str, *, use_browser: bool = False, proxy: str | None = None) -> str:
    """Walk through tiers in order, return first HTML.

    Order:
      1. httpx       — cheap, fast (handles most static pages)
      2. firecrawl   — AI-aware hosted scraping (handles JS + anti-bot)
      3. browser-use — LLM-driven browser (flexible, slow)
      4. playwright  — local browser with stealth (fallback, most powerful)

    Each tier is attempted up to `max_retries` times before moving on.
    Tiers whose dependencies are missing or whose API key is not configured
    are skipped silently after the first attempt.
    """
    ctx = FetchContext(url=url, use_browser=use_browser, proxy=proxy)
    _check_ssrf(url)
    # v186: log strategy selection
    try:
        from .strategy_selector import select_strategy
        _strategy = select_strategy(url)
        logger.info(f"strategy: tier={_strategy["recommended_tier"]} url={url[:60]}")
    except Exception:
        pass
    last_err: str | None = None

    for name, fn in TIERS:
        # Try each tier up to max_retries times
        for attempt in range(1, ctx.max_retries + 1):
            try:
                t0 = time.time()
                html = fn(ctx)
                logger.info(f"tier '{name}' ok in {time.time()-t0:.2f}s len={len(html)} url={url[:80]}")
                return html
            except Exception as e:
                err = repr(e)
                last_err = err
                logger.warning(f"tier '{name}' attempt {attempt} failed: {err}")
                # Skip tier entirely if it's not installed/configured
                if "not installed" in err or "not configured" in err:
                    break
                # Otherwise retry
                continue
    raise RuntimeError(f"all tiers exhausted, last error: {last_err}")


def fetch_page_sync(url: str, *, use_browser: bool = False, proxy: str | None = None) -> str:
    """Backwards-compat alias — same as `fetch_page` (already sync)."""
    return fetch_page(url, use_browser=use_browser, proxy=proxy)


async def fetch_page_async(url: str, *, use_browser: bool = False, proxy: str | None = None) -> str:
    """Async wrapper using a thread pool."""
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: fetch_page(url, use_browser=use_browser, proxy=proxy)
    )


# ------------------------------------------------------------------
# Diagnostic — used by the engine test endpoint
# ------------------------------------------------------------------
def diagnose() -> dict:
    """Return a quick status report of each tier's availability."""
    status = {}
    for name, _ in TIERS:
        try:
            if name == "httpx":
                import httpx  # noqa
                status[name] = {"installed": True, "configured": True}
            elif name == "firecrawl":
                from .firecrawl_client import is_enabled
                import importlib
                installed = importlib.util.find_spec("firecrawl") is not None
                status[name] = {"installed": installed, "configured": is_enabled()}
            elif name == "browser-use":
                import importlib
                installed = importlib.util.find_spec("browser_use") is not None
                from .browser_use_client import is_enabled
                status[name] = {"installed": installed, "configured": is_enabled()}
            elif name == "playwright":
                import importlib
                installed = importlib.util.find_spec("playwright") is not None
                from .playwright_client import is_hyperbrowser_enabled
                status[name] = {
                    "installed": installed, "configured": True,
                    "hyperbrowser": is_hyperbrowser_enabled(),
                }
        except Exception as e:
            status[name] = {"installed": False, "configured": False, "error": repr(e)}
    return status


def test_url(url: str, *, tier: str | None = None) -> dict:
    """Test-fetch a URL with a specific tier (or all tiers in sequence).

    Returns: {tier, success, elapsed_ms, html_size, error}
    """
    if tier and tier not in dict(TIERS).keys():
        return {"error": f"unknown tier '{tier}'"}

    target_tiers = [tier] if tier else [name for name, _ in TIERS]
    ctx = FetchContext(url=url, max_retries=1)
    results = []

    for name in target_tiers:
        fn = dict(TIERS)[name]
        t0 = time.time()
        try:
            html = fn(ctx)
            results.append({
                "tier": name, "success": True,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "html_size": len(html),
                "error": None,
            })
            # P1 fix: when testing all tiers (tier=None), continue to next tier
            # instead of breaking after first success. Only break when
            # testing a specific tier (which should also continue to allow
            # the fallback chain to be tested).
            # Now: continue testing remaining tiers in all cases, so user
            # sees the full fallback behavior.
        except Exception as e:
            results.append({
                "tier": name, "success": False,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "html_size": 0,
                "error": repr(e),
            })
    return {"results": results}
