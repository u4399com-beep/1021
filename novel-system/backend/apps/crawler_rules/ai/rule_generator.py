"""AI-powered rule generation (v69) — auto-generate crawler rules from a sample URL.

Strategy:
1. Fetch the page via the crawler engine
2. Analyze HTML structure (find repeating elements → list items)
3. Try common selector patterns (CSS + XPath)
4. Use heuristics to map fields (title/author/cover/intro)
5. Return a candidate rule config for the user to refine
"""
import re
from bs4 import BeautifulSoup


def _find_repeating_items(soup: BeautifulSoup) -> tuple[str, list]:
    """Find the most common repeating HTML structure — likely the book list."""
    # Strategy: find all elements that appear >5 times with the same tag+class
    from collections import Counter
    candidates = []
    for tag in soup.find_all(True):
        cls = " ".join(tag.get("class", []))
        key = f"{tag.name}.{'.'.join(cls.split()[:2])}" if cls else tag.name
        candidates.append(key)
    common = Counter(candidates).most_common(20)
    # Pick the most common with count > 5
    for key, count in common:
        if count < 5:
            continue
        tag_name, _, cls = key.partition(".")
        cls = cls.replace(".", " ") if cls else ""
        if cls:
            selector = f"{tag_name}.{'.'.join(cls.split())}"
        else:
            selector = tag_name
        items = soup.select(selector)
        if len(items) >= 5:
            return selector, items
    # Fallback: ul > li or table > tr
    for sel in ["ul > li", "table tr", "div.item", "div.book-item", "article"]:
        items = soup.select(sel)
        if len(items) >= 3:
            return sel, items
    return "", []


def _extract_field_from_item(item, field_name: str) -> str:
    """Try to extract a field value from a list item using heuristics."""
    if field_name == "book_url":
        a = item.find("a", href=True)
        return a["href"] if a else ""
    if field_name == "book_title":
        for sel in ["h3", "h4", ".title", ".book-name", "a"]:
            el = item.select_one(sel)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        return item.get_text(strip=True)[:50]
    if field_name == "book_author":
        for sel in [".author", "span.author", ".book-author"]:
            el = item.select_one(sel)
            if el:
                return el.get_text(strip=True)
        return ""
    if field_name == "book_cover":
        img = item.find("img")
        return img.get("src", "") or img.get("data-src", "") if img else ""
    return ""


def generate_list_rule(html: str, base_url: str = "") -> dict:
    """Generate a list-page rule config from HTML.
    
    Returns a candidate config dict.
    """
    soup = BeautifulSoup(html, "lxml")
    selector, items = _find_repeating_items(soup)
    if not selector or not items:
        return {"error": "no repeating items found", "item_selector": {}}
    
    # Sample 3 items to verify field extraction
    sample_fields = {"book_url": [], "book_title": [], "book_author": [], "book_cover": []}
    for item in items[:3]:
        for field in sample_fields:
            val = _extract_field_from_item(item, field)
            if val:
                sample_fields[field].append(val)
    
    # Build config
    config = {
        "item_selector": {"type": "css", "expr": selector},
        "book_url": {"type": "css", "expr": "a::attr(href)"},
        "book_title": {"type": "css", "expr": "h3::text, .title::text, a::text"},
    }
    if sample_fields["book_author"]:
        config["book_author"] = {"type": "css", "expr": ".author::text, span.author::text"}
    if sample_fields["book_cover"]:
        config["book_cover"] = {"type": "xpath", "expr": ".//img/@src"}
    
    # Next page
    next_link = soup.select_one("a.next, a[rel=next], .pagination a:last-child")
    if next_link and next_link.get("href"):
        config["next_page"] = {"type": "css", "expr": "a.next::attr(href), a[rel=next]::attr(href)"}
    
    return {
        "target": "list",
        "item_selector_found": selector,
        "items_found": len(items),
        "sample_fields": sample_fields,
        "config": config,
        "confidence": "high" if all(sample_fields[f] for f in ["book_url", "book_title"]) else "medium",
    }


def generate_book_rule(html: str) -> dict:
    """Generate a book-info-page rule config from HTML."""
    soup = BeautifulSoup(html, "lxml")
    config = {}
    
    # Title: look for h1
    h1 = soup.find("h1")
    if h1:
        config["title"] = {"type": "css", "expr": "h1::text"}
    
    # Author: look for common patterns
    for pattern in [".author", "span.author", "#author", ".book-info .author"]:
        el = soup.select_one(pattern)
        if el:
            config["author"] = {"type": "css", "expr": f"{pattern}::text"}
            break
    
    # Cover: first img in a cover-like container
    for pattern in [".cover img", "#fmimg img", ".book-cover img"]:
        el = soup.select_one(pattern)
        if el:
            config["cover"] = {"type": "xpath", "expr": f"//{pattern.replace(' ', '//')}//@src"}
            break
    
    # Intro
    for pattern in [".intro", "#intro", ".summary", ".book-intro"]:
        el = soup.select_one(pattern)
        if el:
            config["intro"] = {"type": "css", "expr": f"{pattern}::text"}
            break
    
    # TOC link
    toc = soup.find("a", href=re.compile(r"chapter|toc|mulu|catalog", re.I))
    if toc:
        config["toc_url"] = {"type": "xpath", "expr": f"//a[contains(@href,'{toc['href'].split('/')[-1]}')]/@href"}
    
    return {
        "target": "book",
        "config": config,
        "fields_found": list(config.keys()),
        "confidence": "high" if "title" in config and "author" in config else "medium",
    }


def generate_toc_rule(html: str) -> dict:
    """Generate a TOC rule config from HTML."""
    soup = BeautifulSoup(html, "lxml")
    # Find repeating list items with links
    selector, items = _find_repeating_items(soup)
    config = {}
    if selector:
        config["item_selector"] = {"type": "css", "expr": selector}
        config["chapter_url"] = {"type": "xpath", "expr": ".//a/@href"}
        config["chapter_title"] = {"type": "css", "expr": "a::text"}
    
    # Detect volume headers
    vol_headers = soup.select(".volume, .v-name, h2:contains('卷'), h3:contains('卷')")
    if vol_headers:
        config["volume_selector"] = {"type": "css", "expr": ".volume, h2, h3"}
    
    return {
        "target": "toc",
        "item_selector_found": selector,
        "items_found": len(items) if selector else 0,
        "config": config,
        "has_volumes": bool(vol_headers),
    }


def generate_chapter_rule(html: str) -> dict:
    """Generate a chapter-content rule config from HTML."""
    soup = BeautifulSoup(html, "lxml")
    config = {}
    
    # Title: h1 or .chapter-title
    for pattern in ["h1", ".chapter-title", "#title", ".chapter-head h1"]:
        el = soup.select_one(pattern)
        if el:
            config["title"] = {"type": "css", "expr": f"{pattern}::text"}
            break
    
    # Content: largest text block
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
            config["content"] = {"type": "css", "expr": f"#{div_id}"}
        elif div_class:
            config["content"] = {"type": "css", "expr": f"div.{div_class.split()[0]}"}
        else:
            config["content"] = {"type": "css", "expr": "div.content"}
    
    return {
        "target": "chapter",
        "config": config,
        "content_chars": best_len,
        "confidence": "high" if best_len > 500 else "low",
    }
