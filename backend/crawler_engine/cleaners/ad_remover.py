"""Ad removal helpers — heuristic selectors."""
from __future__ import annotations

import re
from bs4 import BeautifulSoup

AD_SELECTORS = [
    # Generic ad classes
    "[class*=ad-]", "[class*=ad_]", "[class*=advert]", "[class*=promotion]",
    "[class*=recommend]", "[class*=sidebar]", "[class*=footer-banner]",
    "[id*=ad-]", "[id*=ad_]", "[id*=advert]",
    # Common Chinese novel site ad wrappers
    ".book-tag", ".ad-container", ".copy-text", ".footer-link",
    # Copyright / watermarks
    "[class*=copyright]", "[class*=watermark]",
]

AD_TEXT_PATTERNS = [
    re.compile(r"更多精彩.*关注", re.IGNORECASE | re.DOTALL),
    re.compile(r"请记住.*域名", re.IGNORECASE | re.DOTALL),
    re.compile(r"本书首发.*", re.IGNORECASE | re.DOTALL),
    re.compile(r"扫码.*二维码", re.IGNORECASE | re.DOTALL),
]


def remove_ads(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "lxml")
    for sel in AD_SELECTORS:
        for el in soup.select(sel):
            el.decompose()

    for p in soup.find_all(["p", "div", "span"]):
        text = p.get_text() or ""
        for pat in AD_TEXT_PATTERNS:
            if pat.search(text):
                p.decompose()
                break
    return str(soup)
