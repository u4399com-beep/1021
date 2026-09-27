"""Selector spec — represents a single field selector.

A selector is a dict with `type` and `expr` (and optional `attr` / `template`):
    {"type": "css",    "expr": "div.title::text"}
    {"type": "xpath",  "expr": "//div[@class='title']/text()"}
    {"type": "regex",  "expr": r"<title>(.+?)</title>"}
    {"type": "xpath",  "expr": "//a/@href", "attr": "href"}
    {"type": "css",    "expr": "li.item a", "attr": "href"}
    {"type": "regex",  "expr": r"book/(\\d+)", "template": "{0}"}

For list pages, the top-level `item_selector` defines one row; child selectors
extract from each row's subtree.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup
from lxml import html as lxml_html


@dataclass
class SelectorSpec:
    type: str  # css | xpath | regex | json_path
    expr: str
    attr: str | None = None
    template: str | None = None  # for formatting matched groups
    multi: bool = False          # return list if True
    base_url: str = ""           # for resolving relative URLs

    @classmethod
    def from_dict(cls, d: dict) -> "SelectorSpec | None":
        if not d:
            return None
        return cls(
            type=d.get("type", "css"),
            expr=d.get("expr", ""),
            attr=d.get("attr"),
            template=d.get("template"),
            multi=bool(d.get("multi", False)),
            base_url=d.get("base_url", ""),
        )


# ------------------------------------------------------------------
# Apply a spec to a node-like object (lxml element or soup or raw html)
# ------------------------------------------------------------------
def apply(spec: SelectorSpec, source: Any) -> str | list[str] | None:
    """Apply the spec; return matched string / list of strings.

    `source` can be:
        - str  → treat as raw HTML, parse to lxml tree
        - lxml.etree  → use directly
    """
    if spec.type == "regex":
        return _apply_regex(spec, source)
    if isinstance(source, str):
        source = _parse_html(source)
    if spec.type == "css":
        return _apply_css(spec, source)
    if spec.type == "xpath":
        return _apply_xpath(spec, source)
    if spec.type == "json_path":
        return _apply_json_path(spec, source)
    return None


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------
def _parse_html(html_str: str):
    try:
        return lxml_html.fromstring(html_str)
    except Exception:
        # lxml may fail on fragment; try BeautifulSoup fallback
        soup = BeautifulSoup(html_str, "lxml")
        return lxml_html.fromstring(str(soup))


def _apply_regex(spec: SelectorSpec, source: Any) -> str | list[str] | None:
    text = source if isinstance(source, str) else (
        source.text_content() if hasattr(source, "text_content") else str(source)
    )
    flags = re.MULTILINE | re.DOTALL
    if spec.multi:
        matches = re.findall(spec.expr, text, flags=flags)
        if spec.template and matches:
            matches = [
                spec.template.format(*m) if isinstance(m, tuple) else spec.template.format(m)
                for m in matches
            ]
        return matches
    m = re.search(spec.expr, text, flags=flags)
    if not m:
        return None
    if spec.template:
        return spec.template.format(*m.groups())
    if m.groups():
        return m.group(1)
    return m.group(0)


def _apply_css(spec: SelectorSpec, source: Any) -> str | list[str] | None:
    # CSS via lxml (cssselect) — supports ::text pseudo
    expr = spec.expr
    attr = spec.attr
    # ::text pseudo-element
    extract_text = "::text" in expr
    if extract_text:
        expr = expr.replace("::text", "").strip()
    if "::attr(" in expr:
        # ::attr(href) — extract attr
        import re as _re
        m = _re.search(r"::attr\(([\w-]+)\)", expr)
        if m:
            attr = m.group(1)
            expr = _re.sub(r"::attr\([\w-]+\)", "", expr).strip()

    elements = source.cssselect(expr) if hasattr(source, "cssselect") else []
    return _extract_results(elements, attr, extract_text, spec.multi, spec.base_url)


def _apply_xpath(spec: SelectorSpec, source: Any) -> str | list[str] | None:
    results = source.xpath(spec.expr) if hasattr(source, "xpath") else []
    if not spec.multi:
        if not results:
            return None
        first = results[0]
        if hasattr(first, "text_content"):
            return first.text_content().strip() if not spec.attr else first.get(spec.attr)
        return str(first).strip()
    out = []
    for r in results:
        if hasattr(r, "text_content"):
            v = r.text_content().strip() if not spec.attr else r.get(spec.attr)
        else:
            v = str(r).strip()
        if v:
            out.append(_absolutize(v, spec.base_url))
    return out


def _apply_json_path(spec: SelectorSpec, source: Any) -> str | list[str] | None:
    import json
    if isinstance(source, (bytes, str)):
        try:
            source = json.loads(source)
        except Exception:
            return None
    # Simple dot-path navigation only — for advanced use, import `jsonpath-ng`
    parts = spec.expr.lstrip("$.").split(".")
    cur = source
    for p in parts:
        if isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    if spec.multi and isinstance(cur, list):
        return [str(x) for x in cur]
    return str(cur) if cur is not None else None


def _extract_results(elements, attr, extract_text, multi, base_url):
    if not elements:
        return [] if multi else None
    if not multi:
        el = elements[0]
        if attr:
            return el.get(attr)
        if extract_text:
            return (el.text_content() or "").strip()
        return lxml_html.tostring(el, encoding="unicode").strip()
    out = []
    for el in elements:
        if attr:
            v = el.get(attr)
        elif extract_text:
            v = (el.text_content() or "").strip()
        else:
            v = lxml_html.tostring(el, encoding="unicode")
        if v:
            out.append(_absolutize(v, base_url))
    return out


def _absolutize(url: str, base_url: str) -> str:
    if not base_url or not url:
        return url
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return "https:" + url
    from urllib.parse import urljoin
    return urljoin(base_url, url)
