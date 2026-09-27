"""Playwright client — Tier-3 with optional Hyperbrowser CDP routing."""
from .client import is_enabled, is_hyperbrowser_enabled, scrape_html

__all__ = ["is_enabled", "is_hyperbrowser_enabled", "scrape_html"]
