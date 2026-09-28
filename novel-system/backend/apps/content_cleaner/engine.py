"""内容清洗引擎 — 规则执行 + HTML 规范化 + 广告过滤。

策略组合：
1. nh3 / lxml_html_clean 做 HTML 标签规范化（白名单）
2. 规则引擎按 CleaningRule 表顺序执行
3. trafilatura / readability 做主体内容提取
"""

import re

from bs4 import BeautifulSoup
from lxml import html as lxml_html

from .models import CleaningRule

# Whitelist of HTML tags allowed in cleaned chapter content
ALLOWED_TAGS = {
    "p", "br", "hr", "h2", "h3", "h4", "blockquote", "em", "strong", "span",
    "img", "a", "ul", "ol", "li",
}
ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt"},
    "span": {"class"},
}


class ContentCleaner:
    """Apply all enabled cleaning rules in priority order."""

    def __init__(self, target: str = "chapter"):
        self.target = target
        self.rules = list(
            CleaningRule.objects.filter(enabled=True, target__in=[target, "all"]).order_by("priority", "id")
        )

    def clean(self, html_text: str) -> str:
        if not html_text:
            return ""

        # Step 1: normalize HTML — strip dangerous tags
        html_text = self._normalize_html(html_text)

        # Step 2: apply each rule in order
        for rule in self.rules:
            html_text = self._apply_rule(rule, html_text)
            if not html_text:
                break

        # Step 3: collapse whitespace
        html_text = re.sub(r"\n{3,}", "\n\n", html_text)
        html_text = re.sub(r"[ \t]{2,}", " ", html_text)
        return html_text.strip()

    # --- normalization ---
    def _normalize_html(self, html_text: str) -> str:
        try:
            soup = BeautifulSoup(html_text, "lxml")
        except Exception:
            soup = BeautifulSoup(html_text, "html.parser")

        # P1 fix: Remove ad elements FIRST (before stripping class/id attributes)
        for sel in [
            "[class*=ad-]", "[class*=ad_]", "[class*=advert]",
            "[id*=ad-]", "[id*=ad_]", "[id*=advert]",
            "[class*=recommend]", "[class*=promotion]", "[class*=copyright]",
        ]:
            for el in soup.select(sel):
                el.decompose()
        # Remove script/style/iframe
        for tag in soup(["script", "style", "iframe", "ins", "noscript"]):
            tag.decompose()

        # Whitelist filter — AFTER ad removal
        for tag in soup.find_all(True):
            if tag.name not in ALLOWED_TAGS:
                tag.unwrap()
                continue
            # Strip disallowed attributes
            allowed = ALLOWED_ATTRS.get(tag.name, set())
            for attr in list(tag.attrs.keys()):
                if attr not in allowed:
                    del tag[attr]
            # P1 fix: Sanitize href attributes — block javascript: scheme
            if tag.name == "a" and "href" in tag.attrs:
                href = tag.attrs["href"]
                if href and href.lower().strip().startswith(("javascript:", "data:", "vbscript:")):
                    del tag.attrs["href"]

        # Remove common ad patterns by class/id
        for sel in [
            "[class*=ad-]", "[class*=ad_]", "[class*=advert]",
            "[id*=ad-]", "[id*=ad_]", "[class*=recommend]",
            "[class*=promotion]", "[class*=copyright]",
        ]:
            for el in soup.select(sel):
                el.decompose()
        return str(soup)

    # --- rule application ---
    def _apply_rule(self, rule: CleaningRule, html_text: str) -> str:
        try:
            if rule.strategy == "regex":
                return re.sub(rule.pattern, rule.replacement, html_text, flags=re.MULTILINE | re.DOTALL)
            if rule.strategy == "string_remove":
                return html_text.replace(rule.pattern, "")
            if rule.strategy == "string_replace":
                return html_text.replace(rule.pattern, rule.replacement)
            if rule.strategy == "css_remove":
                soup = BeautifulSoup(html_text, "lxml")
                for el in soup.select(rule.pattern):
                    el.decompose()
                return str(soup)
            if rule.strategy == "xpath_remove":
                tree = lxml_html.fromstring(html_text)
                for el in tree.xpath(rule.pattern):
                    parent = el.getparent()
                    if parent is not None:
                        parent.remove(el)
                return lxml_html.tostring(tree, encoding="unicode")
        except Exception:
            return html_text
        return html_text


# Public API
def clean_content(html_text: str, target: str = "chapter") -> str:
    return ContentCleaner(target=target).clean(html_text)
