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
    auto_solve_captcha: bool = True,
    captcha_max_attempts: int = 3,
) -> str:
    """Scrape using Playwright with stealth, optionally via Hyperbrowser.

    When Hyperbrowser is enabled, the region is chosen automatically based
    on the URL's TLD (see `region_router.pick_region_for`).

    When `auto_solve_captcha=True`, common WAF captcha patterns (GoEdge,
    Cloudflare) are detected and the captcha image is solved automatically
    using the configured backend (2captcha / OCR).
    """
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
                from ..region_router import pick_region_for
                from ..anti_detection.pool import get_hyperbrowser_session
                region = pick_region_for(url)
                session = get_hyperbrowser_session(region=region)
                cdp_url = session["cdp_url"]
                browser = p.chromium.connect_over_cdp(cdp_url)
                logger.info(f"hyperbrowser connected via region={region} url={url[:80]}")
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

        # ─── v23: Auto-solve WAF captchas ──────────────────────
        if auto_solve_captcha:
            for attempt in range(captcha_max_attempts):
                if not _detect_captcha(page):
                    break
                logger.info(f"captcha detected (attempt {attempt+1}/{captcha_max_attempts}) url={url[:80]}")
                solved = _try_solve_captcha(page)
                if not solved:
                    logger.warning(f"captcha solve failed on attempt {attempt+1}")
                    page.wait_for_timeout(2000)
                    continue
                # Wait for page to reload after captcha submit
                page.wait_for_timeout(3000)
                # Check if captcha is gone
                if not _detect_captcha(page):
                    logger.info(f"captcha solved on attempt {attempt+1}")
                    break
                else:
                    logger.warning(f"captcha still present after solve attempt {attempt+1}")

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


# ─── v23: Captcha detection + auto-solve helpers ────────────────────
def _detect_captcha(page) -> bool:
    """Detect common WAF captcha patterns on the current page.

    Checks for:
      - GoEdge WAF (cunshu.la uses this): form#captcha-form
      - Cloudflare: #challenge-form / cf-challenge
      - Generic: img#captcha / input[name=captcha]
    """
    try:
        return bool(page.evaluate("""() => {
            const hasGoEdge = !!document.querySelector('form#captcha-form')
                || !!document.querySelector('input[name="GOEDGE_WAF_CAPTCHA_CODE"]');
            const hasCF = !!document.querySelector('#challenge-form')
                || !!document.querySelector('.cf-turnstile');
            const hasGeneric = !!document.querySelector('img#captcha, .captcha-image, .ui-captcha-image');
            return hasGoEdge || hasCF || hasGeneric;
        }"""))
    except Exception:
        return False


def _try_solve_captcha(page) -> bool:
    """Try to detect the captcha image, solve it, and submit the form.

    Returns True if a captcha was solved and submitted (success of the
    solve itself, not necessarily success of the form submission).
    """
    try:
        from crawler_engine.captcha_solver import solve_captcha
    except ImportError:
        return False

    try:
        # Find the captcha image element
        img_selector = (
            'img#captcha-image, img#ui-captcha-image, '
            'img.captcha-image, .ui-captcha-image img, '
            'img[src*="captcha"], img[src*="CAPTCHA"]'
        )
        img_element = page.query_selector(img_selector)
        if not img_element:
            return False

        # Capture the image as bytes
        img_bytes = img_element.screenshot()
        if not img_bytes:
            return False

        # Solve via captcha_solver
        solution = solve_captcha(img_bytes, prefer="2captcha")
        if not solution:
            # Try OCR fallback
            solution = solve_captcha(img_bytes, prefer="ocr")
        if not solution:
            return False

        # Fill the captcha input
        input_selector = (
            'input[name="GOEDGE_WAF_CAPTCHA_CODE"], '
            'input[name="captcha_code"], '
            'input[name="captcha"], '
            '#captcha-input, .captcha-input'
        )
        input_element = page.query_selector(input_selector)
        if not input_element:
            return False

        input_element.fill(solution)

        # Submit the form
        form_selector = (
            'form#captcha-form, form.captcha-form, '
            'form:has(input[name="captcha_code"]), '
            'form:has(input[name="captcha"])'
        )
        form = page.query_selector(form_selector)
        if form:
            form.evaluate("el => el.submit()")
        else:
            # Press Enter on the input
            input_element.press("Enter")
        return True
    except Exception as e:
        logger.warning(f"captcha solve exception: {e!r}")
        return False
