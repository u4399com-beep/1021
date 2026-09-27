"""Parser factory — builds a unified parser from a rule config dict.

The rule config schema (per target type):

list::
    {
      "url_pattern": "...",     # optional, used by URL range
      "item_selector": {"type": "css", "expr": "ul > li"},
      "book_url":     {"type": "xpath", "expr": ".//a/@href"},
      "book_title":   {"type": "css", "expr": "h3 a::text"},
      "book_author":  {"type": "css", "expr": ".author::text"},
      "book_cover":   {"type": "xpath", "expr": ".//img/@src"},
      "next_page":    {"type": "css", "expr": "a.next::attr(href)"}
    }

book::
    {
      "title":    {"type": "css", "expr": "h1.book-title::text"},
      "author":   {"type": "css", "expr": "span.author::text"},
      "cover":    {"type": "xpath", "expr": "//img[@class='cover']/@src"},
      "intro":    {"type": "css", "expr": "div.intro::text"},
      "category": {"type": "css", "expr": "span.cat::text", "multi": true},
      "keywords": {"type": "css", "expr": "div.tags a::text", "multi": true},
      "status":   {"type": "regex", "expr": "(已完结|连载中)"},
      "last_chapter_title": {"type": "css", "expr": "a.last-chapter::text"},
      "toc_url":  {"type": "xpath", "expr": "//a[contains(@class,'toc')]/@href"}
    }

toc::
    {
      "item_selector": {"type": "css", "expr": "ul.chapter-list li"},
      "volume_selector": {"type": "css", "expr": ".volume, h2:contains('卷')"},   # optional
      "chapter_url":   {"type": "xpath", "expr": ".//a/@href"},
      "chapter_title": {"type": "css", "expr": "a::text"},
      "next_page":     {"type": "css", "expr": "a.next::attr(href)"}
    }

chapter::
    {
      "content": {"type": "css", "expr": "div.content::html", "multi": false},
      "title":   {"type": "css", "expr": "h1::text"},
      "next_page": {"type": "css", "expr": "a.next::attr(href)"}    # chapter content paged
    }
"""
from __future__ import annotations

from typing import Any

from lxml import html as lxml_html

from .selectors import SelectorSpec, apply, _parse_html


def _find_preceding_volume_name(el, volume_elements) -> str | None:
    """For an element, find the closest preceding volume header by walking back.

    Returns the text content of the volume header, or None if no volume
    precedes this element.
    """
    if not volume_elements:
        return None

    # Get the absolute position of `el` and all volume elements in the document
    # by counting preceding nodes.
    # (Cheaper: just walk back through previous siblings + ancestors.)

    # Strategy: build a list of (document_order, name) for volume_elements
    # and find the volume whose document_order is just before el's.
    # document_order = number of preceding elements.

    def _doc_order(elem) -> int:
        # Count of preceding elements in document order
        count = 0
        cur = elem
        while cur is not None:
            # Iterate through previous siblings
            sib = cur.getprevious()
            while sib is not None:
                count += 1 + len(sib.xpath(".//*"))
                sib = sib.getprevious()
            cur = cur.getparent()
            if cur is not None:
                count += 1
        return count

    el_order = _doc_order(el)
    closest = None
    closest_order = -1
    for vol_el in volume_elements:
        vol_order = _doc_order(vol_el)
        if vol_order < el_order and vol_order > closest_order:
            closest = vol_el
            closest_order = vol_order

    if closest is None:
        return None
    # Extract text content
    return closest.text_content().strip() if hasattr(closest, "text_content") else (closest.text or "").strip()


class Parser:
    """Apply a single rule config to a piece of HTML."""

    def __init__(self, config: dict):
        self.config = config or {}

    def parse(self, target: str, html: str, *, base_url: str = "") -> Any:
        if target == "list":
            return self._parse_list(html, base_url)
        if target == "book":
            return self._parse_book(html, base_url)
        if target == "toc":
            return self._parse_toc(html, base_url)
        if target == "chapter":
            return self._parse_chapter(html, base_url)
        raise ValueError(f"unknown target {target}")

    # ------------------------------------------------------------------
    # List page
    # ------------------------------------------------------------------
    def _parse_list(self, html: str, base_url: str) -> dict:
        item_spec = SelectorSpec.from_dict(self.config.get("item_selector", {}))
        if not item_spec:
            return {"items": []}
        tree = _parse_html(html)
        items = []
        for el in tree.cssselect(item_spec.expr) if hasattr(tree, "cssselect") else []:
            item = {}
            for field in ("book_url", "book_title", "book_author", "book_cover"):
                spec_d = self.config.get(field)
                if not spec_d:
                    continue
                spec = SelectorSpec.from_dict(spec_d)
                spec.base_url = base_url
                v = apply(spec, el)
                item[field.replace("book_", "")] = v
            items.append(item)
        next_spec = SelectorSpec.from_dict(self.config.get("next_page", {}))
        next_url = apply(next_spec, tree) if next_spec else None
        return {"items": items, "next_page": next_url}

    # ------------------------------------------------------------------
    # Book info page
    # ------------------------------------------------------------------
    def _parse_book(self, html: str, base_url: str) -> dict:
        tree = _parse_html(html)
        out = {}
        for field in ("title", "author", "cover", "intro", "category",
                      "keywords", "status", "last_chapter_title", "toc_url"):
            spec_d = self.config.get(field)
            if not spec_d:
                continue
            spec = SelectorSpec.from_dict(spec_d)
            spec.base_url = base_url
            out[field] = apply(spec, tree)
        return out

    # ------------------------------------------------------------------
    # Table of contents — supports volume grouping
    # ------------------------------------------------------------------
    def _parse_toc(self, html: str, base_url: str) -> dict:
        item_spec = SelectorSpec.from_dict(self.config.get("item_selector", {}))
        vol_spec = SelectorSpec.from_dict(self.config.get("volume_selector", {}))
        tree = _parse_html(html)

        # If volume_selector is configured, we parse in two passes:
        # Pass 1: find all volume headers and their positions in the DOM
        # Pass 2: walk all chapter items, assign each to the volume header
        #         that appears immediately before it in the document order.
        chapters = []
        next_spec = SelectorSpec.from_dict(self.config.get("next_page", {}))
        next_url = apply(next_spec, tree) if next_spec else None

        if vol_spec and hasattr(tree, "cssselect"):
            volume_elements = tree.cssselect(vol_spec.expr) if hasattr(tree, "cssselect") else []
            # For each chapter item, find the closest preceding volume element
            for el in (tree.cssselect(item_spec.expr) if hasattr(tree, "cssselect") else []):
                ch = {}
                for field in ("chapter_url", "chapter_title"):
                    spec_d = self.config.get(field)
                    if not spec_d:
                        continue
                    spec = SelectorSpec.from_dict(spec_d)
                    spec.base_url = base_url
                    ch[field.replace("chapter_", "")] = apply(spec, el)

                # Find the closest preceding volume element by walking back through siblings
                volume_name = _find_preceding_volume_name(el, volume_elements)
                ch["volume"] = volume_name
                chapters.append(ch)
        else:
            for el in (tree.cssselect(item_spec.expr) if hasattr(tree, "cssselect") else []):
                ch = {}
                for field in ("chapter_url", "chapter_title"):
                    spec_d = self.config.get(field)
                    if not spec_d:
                        continue
                    spec = SelectorSpec.from_dict(spec_d)
                    spec.base_url = base_url
                    ch[field.replace("chapter_", "")] = apply(spec, el)
                chapters.append(ch)

        return {"chapters": chapters, "next_page": next_url}

    # ------------------------------------------------------------------
    # Chapter content page
    # ------------------------------------------------------------------
    def _parse_chapter(self, html: str, base_url: str) -> dict:
        tree = _parse_html(html)
        out = {}
        for field in ("title", "content", "next_page"):
            spec_d = self.config.get(field)
            if not spec_d:
                continue
            spec = SelectorSpec.from_dict(spec_d)
            spec.base_url = base_url
            out[field] = apply(spec, tree)
        return out


def build_parser(config: dict) -> Parser:
    return Parser(config)
