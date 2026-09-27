"""Search engine suggestion fetcher — baidu / bing / google / sogou autocomplete."""
from __future__ import annotations

import httpx
from loguru import logger


BAIDU_SUGGEST = "https://suggestion.baidu.com/su?wd={kw}&action=opensearch&ie=UTF-8"
BING_SUGGEST = "https://api.bing.com/osjson.aspx?query={kw}"
GOOGLE_SUGGEST = "https://suggestqueries.google.com/complete/search?client=firefox&q={kw}"
SOGOU_SUGGEST = "https://sor.html5.sogou.com/sugg?key={kw}"


def _safe_get(url: str) -> str:
    try:
        r = httpx.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            return r.text
    except Exception as e:
        logger.warning(f"suggest failed {url}: {e!r}")
    return ""


def _parse_jsonp(text: str, fallback_prefix: str = "window.baidu.sug(") -> list[str]:
    """Strip JSONP wrapper, return list of suggestion strings."""
    import json
    text = text.strip()
    if text.startswith(fallback_prefix):
        text = text[len(fallback_prefix):]
    if text.endswith(");") or text.endswith(")"):
        text = text.rstrip(");").rstrip(")")
    try:
        return json.loads(text).get("s") or json.loads(text).get("results") or []
    except Exception:
        return []


def fetch_baidu(kw: str) -> list[str]:
    text = _safe_get(BAIDU_SUGGEST.format(kw=kw))
    return _parse_jsonp(text, "window.baidu.sug(")


def fetch_bing(kw: str) -> list[str]:
    text = _safe_get(BING_SUGGEST.format(kw=kw))
    try:
        import json
        out = json.loads(text)
        if isinstance(out, list) and len(out) >= 2:
            return out[1]
    except Exception:
        pass
    return []


def fetch_google(kw: str) -> list[str]:
    text = _safe_get(GOOGLE_SUGGEST.format(kw=kw))
    try:
        import json
        out = json.loads(text)
        if isinstance(out, list) and len(out) >= 2:
            return out[1]
    except Exception:
        pass
    return []


def fetch_sogou(kw: str) -> list[str]:
    text = _safe_get(SOGOU_SUGGEST.format(kw=kw))
    try:
        import json
        out = json.loads(text)
        return out.get("results") or []
    except Exception:
        return []


PROVIDERS = {
    "baidu": fetch_baidu,
    "bing": fetch_bing,
    "google": fetch_google,
    "sogou": fetch_sogou,
}


def fetch_all(kw: str, providers: list[str] | None = None) -> dict[str, list[str]]:
    """Return all suggestions from multiple providers."""
    providers = providers or ["baidu", "bing", "google", "sogou"]
    return {p: PROVIDERS[p](kw) for p in providers if p in PROVIDERS}
