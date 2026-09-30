"""Intelligent strategy selector (v178) — auto-choose best fetch tier."""


def select_strategy(url, known_waf=""):
    if known_waf:
        from .anti_detection.cloudflare_bypass import get_bypass_strategy
        strategy = get_bypass_strategy(known_waf)
        return {
            "recommended_tier": strategy["tier"],
            "reason": f"WAF detected: {known_waf}",
            "fallback_tiers": ["playwright", "browser-use"],
            "wait_seconds": strategy.get("wait_seconds", 0),
        }
    from .region_router import pick_region_for
    region = pick_region_for(url)
    return {
        "recommended_tier": "httpx",
        "reason": "no known WAF, try fast httpx first",
        "fallback_tiers": ["firecrawl", "playwright"],
        "region": region,
        "wait_seconds": 0,
    }


def should_switch_tier(url, error, current_tier):
    e = (error or "").lower()
    if "403" in e or "forbidden" in e:
        return {"switch_to": "playwright", "reason": "403 — need browser"}
    if "timeout" in e:
        return {"switch_to": "httpx", "reason": "timeout — try lighter"}
    if "captcha" in e or "waf" in e:
        return {"switch_to": "playwright", "reason": "WAF — need browser"}
    if "connection" in e:
        return {"switch_to": "playwright", "reason": "connection error"}
    return {"switch_to": None, "reason": "unknown, continue fallback"}
