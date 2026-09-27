"""Playwright client wrapper — Tier-3 local browser automation with stealth.

Hyperbrowser integration: when HYPERBROWSER_API_KEY is configured, we route
through Hyperbrowser's hosted browser pool instead of running a local browser.
This bypasses many anti-bot signals (residential IPs, real fingerprints, etc).
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    """Playwright is always available as fallback if `playwright` is installed."""
    try:
        import playwright  # noqa
        return True
    except ImportError:
        return False


def is_hyperbrowser_enabled() -> bool:
    return bool(settings.CRAWLER.get("HYPERBROWSER_API_KEY", ""))


def _connect_hyperbrowser():
    """Connect to a Hyperbrowser hosted browser pool via CDP endpoint."""
    api_key = settings.CRAWLER.get("HYPERBROWSER_API_KEY", "")
    if not api_key:
        raise RuntimeError("HYPERBROWSER_API_KEY not configured")
    # Hyperbrowser provides a CDP endpoint per session — see https://docs.hyperbrowser.ai
    # We use a simple session-create + connect pattern here.
    import httpx

    create_url = "https://api.hyperbrowser.dev/v1/sessions"
    r = httpx.post(
        create_url,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"sessionOptions": {"solve_captchas": True, "proxy": "auto"}},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"hyperbrowser: failed to create session: {r.text}")
    data = r.json()
    cdp_url = data.get("cdpUrl") or data.get("wsEndpoint")
    if not cdp_url:
        raise RuntimeError("hyperbrowser: no cdpUrl in response")
    return cdp_url


def scrape_html(
    url: str,
    *,
    use_browser: bool = True,
    proxy: str | None = None,
    timeout: int = 30,
    wait_extra_ms: int = 1500,
) -> str:
    """Scrape using Playwright with stealth, optionally via Hyperbrowser."""
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "playwright is not installed. Run `pip install playwright` "
            "and `playwright install chromium` to enable the Playwright tier."
        ) from e

    ua_pool = settings.CRAWLER.get("USER_AGENTS", [])
    import random
    ua = random.choice(ua_pool) if ua_pool else (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    )

    with sync_playwright() as p:
        # If Hyperbrowser is configured, connect remotely instead of launching locally
        if is_hyperbrowser_enabled():
            try:
                cdp_url = _connect_hyperbrowser()
                browser = p.chromium.connect_over_cdp(cdp_url)
            except Exception as e:
                logger.warning(f"hyperbrowser connection failed, falling back to local: {e!r}")
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
        else:
            launch_args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
            if proxy:
                launch_args.append(f"--proxy-server={proxy}")
            browser = p.chromium.launch(args=launch_args, headless=True)

        context = browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
            },
        )

        page = context.new_page()
        try:
            Stealth().apply(page)  # type: ignore
        except Exception:
            pass

        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        page.wait_for_timeout(wait_extra_ms)

        # Auto-scroll to trigger lazy-loaded content
        try:
            page.evaluate("""
                async () => {
                    await new Promise(resolve => {
                        let total = 0, step = 600;
                        const t = setInterval(() => {
                            window.scrollBy(0, step);
                            total += step;
                            if (total >= document.body.scrollHeight) {
                                clearInterval(t); resolve();
                            }
                        }, 100);
                    });
                }
            """)
            page.wait_for_timeout(300)
        except Exception:
            pass

        html = page.content()
        browser.close()
        return html
