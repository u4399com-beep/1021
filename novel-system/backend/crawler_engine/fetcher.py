"""crawler_engine — three-tier fetch with fallback.

Tier 1: Firecrawl (fast, AI-aware, hosted)
Tier 2: Browser Use (LLM-driven browser automation)
Tier 3: Playwright + Hyperbrowser (local browser with anti-detection)

Each tier receives a `RetryContext` and either returns HTML or raises. The
parent fetcher walks the tiers in order and stops at the first success.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

from loguru import logger

from .anti_detection.pool import get_cookie, get_user_agent


# ------------------------------------------------------------------
# Retry context
# ------------------------------------------------------------------
@dataclass
class RetryContext:
    url: str
    method: str = "GET"
    headers: dict | None = None
    timeout: int = 30
    use_browser: bool = False  # hint: site requires JS rendering
    max_retries: int = 3
    raw_headers: bool = False
    proxy: Optional[str] = None
    last_error: Optional[str] = None

    def with_retry(self):
        return range(self.max_retries)


# ------------------------------------------------------------------
# Tier 1 — Firecrawl
# ------------------------------------------------------------------
def fetch_with_firecrawl(ctx: RetryContext) -> str:
    """Try Firecrawl first. Requires FIRECRAWL_API_KEY configured."""
    from django.conf import settings

    api_key = settings.CRAWLER.get("FIRECRAWL_API_KEY", "")
    if not api_key:
        raise RuntimeError("firecrawl disabled: no API key")

    try:
        from firecrawl import FirecrawlApp  # type: ignore
    except ImportError:
        raise RuntimeError("firecrawl-py not installed")

    app = FirecrawlApp(api_key=api_key, api_url=settings.CRAWLER["FIRECRAWL_API_URL"])
    result = app.scrape_url(
        ctx.url,
        params={"formats": ["html"], "waitFor": 2000},
    )
    if not result or "html" not in result:
        raise RuntimeError("firecrawl empty response")
    return result["html"]


# ------------------------------------------------------------------
# Tier 2 — Browser Use
# ------------------------------------------------------------------
def fetch_with_browser_use(ctx: RetryContext) -> str:
    """LLM-driven browser — slow but flexible for sites with complex anti-bot."""
    from django.conf import settings

    api_key = settings.CRAWLER.get("BROWSER_USE_OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("browser-use disabled: no OpenAI key")

    try:
        import os
        os.environ.setdefault("OPENAI_API_KEY", api_key)
        from browser_use import Agent  # type: ignore
        from langchain_openai import ChatOpenAI  # type: ignore
    except ImportError:
        raise RuntimeError("browser-use not installed")

    async def _run():
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        agent = Agent(
            task=f"Navigate to {ctx.url} and return the full HTML.",
            llm=llm,
        )
        result = await agent.run()
        return str(result)

    return asyncio.get_event_loop().run_until_complete(_run())


# ------------------------------------------------------------------
# Tier 3 — Playwright + Hyperbrowser
# ------------------------------------------------------------------
def fetch_with_playwright(ctx: RetryContext) -> str:
    """Local Playwright with stealth + optional Hyperbrowser proxy."""
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth  # type: ignore
    except ImportError:
        raise RuntimeError("playwright not installed")

    ua = get_user_agent()
    cookie = get_cookie()

    with sync_playwright() as p:
        browser_args = ["--no-sandbox", "--disable-dev-shm-usage"]
        if ctx.proxy:
            browser_args.append(f"--proxy-server={ctx.proxy}")
        if not ctx.use_browser:
            # headless unless explicitly hinted
            browser = p.chromium.launch(args=browser_args, headless=True)
        else:
            browser = p.chromium.launch(args=browser_args, headless=True)

        context = browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        if cookie:
            context.add_cookies([{
                "name": k, "value": v, "domain": ".{ctx.url.split('/')[2]}",
                "path": "/",
            } for k, v in cookie.items()])

        page = context.new_page()
        try:
            Stealth().apply(page)  # type: ignore
        except Exception:
            pass

        page.goto(ctx.url, wait_until="domcontentloaded", timeout=ctx.timeout * 1000)
        page.wait_for_timeout(1500)  # grace period for JS
        html = page.content()
        browser.close()
        return html


# ------------------------------------------------------------------
# Tier 0 (cheap) — requests/httpx
# ------------------------------------------------------------------
def fetch_with_requests(ctx: RetryContext) -> str:
    import httpx

    headers = {
        "User-Agent": get_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    }
    if ctx.headers:
        headers.update(ctx.headers)

    with httpx.Client(timeout=ctx.timeout, follow_redirects=True) as client:
        r = client.get(ctx.url, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"http {r.status_code}")
        return r.text


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------
TIERS = (
    fetch_with_requests,
    fetch_with_firecrawl,
    fetch_with_browser_use,
    fetch_with_playwright,
)


def fetch_page(url: str, *, use_browser: bool = False, proxy: str | None = None) -> str:
    """Walk through tiers in order, return first HTML.

    Order:
      1. requests/httpx (cheap, fast) — handles most static pages
      2. firecrawl — AI-aware, may bypass some anti-bot
      3. browser-use — flexible, slow
      4. playwright+stealth — fallback, most powerful
    """
    ctx = RetryContext(url=url, use_browser=use_browser, proxy=proxy)
    last_err = None
    for idx, tier_fn in enumerate(TIERS):
        for attempt in ctx.with_retry():
            try:
                t0 = time.time()
                html = tier_fn(ctx)
                logger.info(f"tier{idx} {tier_fn.__name__} ok in {time.time()-t0:.2f}s len={len(html)}")
                return html
            except Exception as e:
                last_err = repr(e)
                logger.warning(f"tier{idx} {tier_fn.__name__} attempt {attempt+1} failed: {last_err}")
                # Don't retry tiers that aren't installed
                if "not installed" in last_err or "disabled" in last_err:
                    break
    raise RuntimeError(f"all tiers exhausted: {last_err}")


def fetch_page_sync(url: str, *, use_browser: bool = False, proxy: str | None = None) -> str:
    """Synchronous wrapper — same as fetch_page (already sync)."""
    return fetch_page(url, use_browser=use_browser, proxy=proxy)


async def fetch_page_async(url: str, *, use_browser: bool = False, proxy: str | None = None) -> str:
    """Async wrapper using a thread pool."""
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: fetch_page(url, use_browser=use_browser, proxy=proxy)
    )
