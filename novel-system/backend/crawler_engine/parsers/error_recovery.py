"""Parser error recovery (v138) — graceful degradation when selectors fail."""
from __future__ import annotations
from typing import Any
from loguru import logger


def safe_parse(parser_fn, html: str, target: str, **kwargs) -> dict:
    """Wrap a parser function with error recovery.

    If the primary parse fails, try fallback strategies:
    1. Re-parse with lxml instead of html.parser
    2. Strip dangerous HTML entities first
    3. Return empty result with error field
    """
    try:
        result = parser_fn(target, html, **kwargs)
        if result:
            return result
    except Exception as e:
        logger.warning(f"parse failed (primary): {e!r}")
    
    # Fallback 1: try with html.parser
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        clean_html = str(soup)
        result = parser_fn(target, clean_html, **kwargs)
        if result:
            return result
    except Exception as e:
        logger.warning(f"parse failed (fallback html.parser): {e!r}")
    
    # Fallback 2: strip scripts/styles and retry
    try:
        import re
        clean = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
        result = parser_fn(target, clean, **kwargs)
        if result:
            return result
    except Exception as e:
        logger.warning(f"parse failed (fallback strip): {e!r}")
    
    return {"error": "all parse strategies failed", "target": target}
