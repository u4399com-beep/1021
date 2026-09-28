"""Rule recommender (v154) — suggest rules based on page structure analysis."""
from __future__ import annotations
from bs4 import BeautifulSoup
from collections import Counter
from typing import Any


def analyze_page_structure(html: str) -> dict:
    """Analyze HTML structure and suggest a rule configuration.
    
    Returns a diagnostic dict with:
    - detected list selectors
    - detected field patterns
    - suggested config
    """
    soup = BeautifulSoup(html, "lxml")
    
    # 1. Find repeating elements (likely list items)
    element_counts = Counter()
    for tag in soup.find_all(True):
        cls = " ".join(tag.get("class", [])[:2])
        key = f"{tag.name}.{cls}" if cls else tag.name
        element_counts[key] += 1
    
    # Top repeating elements
    top_elements = element_counts.most_common(10)
    repeating = [(k, v) for k, v in top_elements if v >= 5]
    
    # 2. Detect field patterns
    fields = {}
    
    # Title: look for h1/h2/h3 or .title class
    for sel in ["h1", "h2", "h3", ".title", ".book-name", ".book-title"]:
        el = soup.select_one(sel)
        if el:
            fields["title_selector"] = sel
            break
    
    # Author: look for .author
    for sel in [".author", "span.author", ".book-author", "#author"]:
        el = soup.select_one(sel)
        if el:
            fields["author_selector"] = sel
            break
    
    # Content: find largest text block
    best_div, best_len = None, 0
    for div in soup.find_all(["div", "article", "section"]):
        text_len = len(div.get_text(strip=True))
        if text_len > best_len:
            best_div = div
            best_len = text_len
    if best_div:
        div_id = best_div.get("id", "")
        div_class = " ".join(best_div.get("class", []))
        if div_id:
            fields["content_selector"] = f"#{div_id}"
        elif div_class:
            fields["content_selector"] = f"div.{div_class.split()[0]}"
    
    return {
        "repeating_elements": repeating,
        "detected_fields": fields,
        "suggested_item_selector": repeating[0][0] if repeating else None,
        "confidence": "high" if repeating and fields else "low",
    }
