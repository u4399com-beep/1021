"""Cloudflare detection and bypass (v155)."""
from __future__ import annotations
import re
from typing import Any
from loguru import logger


CLOUDFLARE_PATTERNS = [
    "cf-challenge",
    "cf-mitigated",
    "cf-ray",
    "cloudflare",
    "__cf_bm",
    "Just a moment...",
    "Checking your browser",
    "cf-turnstile",
]

WAF_PATTERNS = {
    "goedge": ["GOEDGE_WAF_CAPTCHA", "captcha-form", "ui-captcha-image"],
    "modsecurity": ["Mod_Security", "mod_security"],
    "akamai": ["Akamai", "akamai"],
    "incapsula": ["incap_ses", "Incapsula"],
    "yundun": ["yundun", "jsl_clearance_s"],
}


def detect_waf(html: str, headers: dict = None) -> dict:
    """Detect what WAF/anti-bot system is in use.
    
    Returns: {waf_type: str|None, confidence: float, evidence: [...]}
    """
    html_lower = (html or "").lower()
    headers = headers or {}
    all_headers = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
    
    evidence = []
    waf_type = None
    
    # Check Cloudflare
    for pattern in CLOUDFLARE_PATTERNS:
        if pattern.lower() in html_lower or pattern.lower() in all_headers:
            waf_type = "cloudflare"
            evidence.append(f"cloudflare pattern: {pattern}")
            break
    
    # Check other WAFs
    if not waf_type:
        for name, patterns in WAF_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in html_lower:
                    waf_type = name
                    evidence.append(f"{name} pattern: {pattern}")
                    break
            if waf_type:
                break
    
    # Check HTTP status codes that indicate WAF
    if not waf_type:
        if "403" in html_lower and "forbidden" in html_lower:
            waf_type = "unknown_403"
            evidence.append("403 Forbidden without known WAF signature")
        elif "429" in html_lower:
            waf_type = "rate_limited"
            evidence.append("429 rate limited")
    
    confidence = 0.9 if waf_type else 0.0
    
    return {
        "waf_type": waf_type,
        "confidence": confidence,
        "evidence": evidence,
    }


def get_bypass_strategy(waf_type: str) -> dict:
    """Return recommended bypass strategy for a WAF type."""
    strategies = {
        "cloudflare": {
            "tier": "playwright",
            "wait_seconds": 5,
            "needs_js": True,
            "needs_captcha": False,
            "notes": "Use Playwright with stealth. Wait for challenge to resolve.",
        },
        "goedge": {
            "tier": "playwright",
            "wait_seconds": 3,
            "needs_js": True,
            "needs_captcha": True,
            "notes": "Use Playwright + captcha solver. GoEdge requires captcha on first visit.",
        },
        "unknown_403": {
            "tier": "playwright",
            "wait_seconds": 2,
            "needs_js": True,
            "needs_captcha": False,
            "notes": "Try Playwright with stealth. May need cookies.",
        },
        "rate_limited": {
            "tier": "httpx",
            "wait_seconds": 30,
            "needs_js": False,
            "needs_captcha": False,
            "notes": "Wait 30s and retry with different UA + proxy.",
        },
    }
    return strategies.get(waf_type, {
        "tier": "playwright",
        "wait_seconds": 3,
        "needs_js": True,
        "needs_captcha": False,
        "notes": "Default: use Playwright with stealth.",
    })
