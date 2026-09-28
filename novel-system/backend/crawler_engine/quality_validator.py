"""Crawl result quality validator (v179) — verify fetched content is usable."""
from __future__ import annotations
from typing import Any


def validate_book_data(book_data):
    issues = []
    if not book_data:
        return {"valid": False, "issues": ["empty result"]}
    title = book_data.get("title", "")
    if not title:
        issues.append("missing title")
    elif len(title) < 2:
        issues.append(f"title too short: {title}")
    elif len(title) > 500:
        issues.append(f"title too long: {len(title)}")
    intro = book_data.get("intro", "")
    if intro and len(intro) < 10:
        issues.append("intro suspiciously short")
    cover = book_data.get("cover", "")
    if not cover:
        issues.append("no cover URL")
    return {"valid": len(issues) == 0, "issues": issues, "score": max(0, 100 - len(issues) * 20)}


def validate_chapter_data(ch_data):
    issues = []
    if not ch_data:
        return {"valid": False, "issues": ["empty result"]}
    title = ch_data.get("title", "")
    if not title:
        issues.append("missing title")
    content = ch_data.get("content", "")
    if not content:
        issues.append("empty content")
    elif len(content) < 100:
        issues.append(f"content too short: {len(content)} chars")
    elif len(content) > 500000:
        issues.append(f"content too long: {len(content)} chars")
    if "<html" in content.lower()[:200]:
        issues.append("full HTML page in content")
    if "<script" in content.lower():
        issues.append("script tag in content")
    return {"valid": len(issues) == 0, "issues": issues, "score": max(0, 100 - len(issues) * 15)}


def validate_list_data(list_data):
    items = list_data.get("items", [])
    issues = []
    if not items:
        return {"valid": False, "issues": ["no items found"]}
    for i, item in enumerate(items[:5]):
        if not item.get("url"):
            issues.append(f"item {i}: missing URL")
        if not item.get("title"):
            issues.append(f"item {i}: missing title")
    return {"valid": len(issues) == 0, "issues": issues, "item_count": len(items)}
