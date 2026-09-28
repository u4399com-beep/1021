"""Deep Playwright stealth config (v136) — hide automation signals."""
from __future__ import annotations
import random
from typing import Any


# CDP commands to hide automation
STEALTH_CDP_COMMANDS = [
    # Hide webdriver flag
    {"method": "Page.addScriptToEvaluateOnNewDocument",
     "params": {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}},
    # Override plugins to look real
    {"method": "Page.addScriptToEvaluateOnNewDocument",
     "params": {"source": """
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                {name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer'},
                {name: 'Native Client', filename: 'internal-pdf-viewer'},
            ]
        })
    """}},
    # Override languages
    {"method": "Page.addScriptToEvaluateOnNewDocument",
     "params": {"source": """
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']})
    """}},
    # Override permissions
    {"method": "Page.addScriptToEvaluateOnNewDocument",
     "params": {"source": """
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({state: Notification.permission})
                : originalQuery(parameters)
    """}},
    # Hide Chrome runtime
    {"method": "Page.addScriptToEvaluateOnNewDocument",
     "params": {"source": "window.chrome = {runtime: {}}"}},
    # Override WebGL vendor
    {"method": "Page.addScriptToEvaluateOnNewDocument",
     "params": {"source": """
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, parameter);
        }
    """}},
]


def apply_stealth_cdp(page) -> None:
    """Apply all stealth CDP commands to a Playwright page."""
    for cmd in STEALTH_CDP_COMMANDS:
        try:
            # Use the page's underlying CDP session
            client = page.context.new_cdp_session(page)
            client.send(cmd["method"], cmd["params"])
        except Exception:
            pass


def get_random_fingerprint() -> dict:
    """Return a randomized fingerprint config for Playwright context."""
    return {
        "viewport": {
            "width": random.choice([1366, 1440, 1536, 1600, 1920]),
            "height": random.choice([768, 900, 864, 1080]),
        },
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "extra_http_headers": {
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="127", "Not)A;Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        },
    }
