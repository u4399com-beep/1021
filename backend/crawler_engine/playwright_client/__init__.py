"""Playwright client — Tier-3 with optional Hyperbrowser CDP routing."""
from .client import (
    _detect_captcha,
    _try_solve_captcha,
    is_enabled,
    is_hyperbrowser_enabled,
    scrape_html,
)

__all__ = [
    "_detect_captcha",
    "_try_solve_captcha",
    "is_enabled",
    "is_hyperbrowser_enabled",
    "scrape_html",
]
