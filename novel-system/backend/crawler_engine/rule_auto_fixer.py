"""Rule auto-fixer (v146) — automatically repair broken selectors.

When a rule test fails, analyze the error and suggest fixes:
1. CSS selector not found → try parent/child selectors
2. XPath returns empty → try alternative axis
3. Regex no match → relax pattern
"""
from bs4 import BeautifulSoup


def analyze_parse_failure(html: str, config: dict, target: str) -> dict:
    """Analyze why a parse returned empty and suggest fixes."""
    soup = BeautifulSoup(html, "lxml")
    suggestions = []

    item_sel = config.get("item_selector", {})
    if item_sel:
        sel_type = item_sel.get("type", "css")
        expr = item_sel.get("expr", "")
        if sel_type == "css":
            # Check if selector matches anything
            items = soup.select(expr)
            if not items:
                # Try common variations
                for variation in [
                    expr.replace("::text", "").strip(),
                    "li" if "li" in expr else "div.item",
                    "ul li", "table tr",
                ]:
                    test = soup.select(variation)
                    if test:
                        suggestions.append({
                            "type": "item_selector",
                            "old": expr,
                            "new": variation,
                            "found": len(test),
                        })
                        break
        elif sel_type == "xpath":
            from lxml import html as lxml_html
            try:
                tree = lxml_html.fromstring(html)
                items = tree.xpath(expr)
                if not items:
                    # Try simpler xpath
                    for variation in ["//li", "//tr", "//div[@class]", "//a"]:
                        test = tree.xpath(variation)
                        if test:
                            suggestions.append({
                                "type": "item_selector",
                                "old": expr,
                                "new": variation,
                                "found": len(test),
                            })
                            break
            except Exception:
                pass

    return {
        "target": target,
        "suggestions": suggestions,
        "has_fix": len(suggestions) > 0,
    }


def auto_fix_rule(config: dict, html: str, target: str) -> dict:
    """Try to auto-fix a rule config based on HTML analysis."""
    analysis = analyze_parse_failure(html, config, target)
    if not analysis["has_fix"]:
        return {"fixed": False, "config": config, "suggestions": []}

    new_config = dict(config)
    for s in analysis["suggestions"]:
        if s["type"] == "item_selector":
            new_config["item_selector"]["expr"] = s["new"]

    return {"fixed": True, "config": new_config, "suggestions": analysis["suggestions"]}
