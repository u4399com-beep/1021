"""Chapter quality scoring (v56) — assess content quality on a 0-100 scale."""
from __future__ import annotations
import re


def score_chapter(content: str) -> dict:
    """Score a chapter's content quality.
    
    Returns: {score: 0-100, details: {...}}
    """
    if not content:
        return {"score": 0, "details": {"reason": "empty content"}}
    
    details = {}
    score = 100
    
    # Length check (500-50000 chars is ideal)
    length = len(content)
    if length < 500:
        score -= 30
        details["length"] = f"too_short ({length} chars)"
    elif length < 1000:
        score -= 15
        details["length"] = f"short ({length} chars)"
    elif length > 100000:
        score -= 10
        details["length"] = f"very_long ({length} chars)"
    else:
        details["length"] = f"ok ({length} chars)"
    
    # HTML tag ratio (too many tags = parsing issue)
    tags = re.findall(r"<[^>]+>", content)
    tag_chars = sum(len(t) for t in tags)
    if length > 0:
        tag_ratio = tag_chars / length
        if tag_ratio > 0.5:
            score -= 20
            details["tag_ratio"] = f"too_high ({tag_ratio:.1%})"
        elif tag_ratio > 0.3:
            score -= 10
            details["tag_ratio"] = f"high ({tag_ratio:.1%})"
        else:
            details["tag_ratio"] = f"ok ({tag_ratio:.1%})"
    
    # Script/style contamination
    if "<script" in content.lower():
        score -= 15
        details["script_contamination"] = True
    if "<style" in content.lower():
        score -= 10
        details["style_contamination"] = True
    
    # Paragraph structure
    paragraphs = re.findall(r"<p[^>]*>", content) or content.split("\n\n")
    if len(paragraphs) < 3:
        score -= 10
        details["paragraphs"] = f"few ({len(paragraphs)})"
    else:
        details["paragraphs"] = f"ok ({len(paragraphs)})"
    
    # Repetition detection (same line repeated >3 times)
    lines = [l.strip() for l in content.replace("<br>", "\n").split("\n") if l.strip()]
    if lines:
        from collections import Counter
        line_counts = Counter(lines)
        max_repeat = max(line_counts.values())
        if max_repeat > 5:
            score -= 15
            details["repetition"] = f"high (line repeated {max_repeat}x)"
    
    # Ad keywords
    ad_keywords = ["更多精彩", "请记住", "本书首发", "扫码", "微信公众号", "QQ群"]
    ad_hits = sum(1 for kw in ad_keywords if kw in content)
    if ad_hits > 0:
        score -= 5 * ad_hits
        details["ad_keywords"] = f"{ad_hits} found"
    
    score = max(0, min(100, score))
    details["final_score"] = score
    
    if score >= 80:
        details["grade"] = "A"
    elif score >= 60:
        details["grade"] = "B"
    elif score >= 40:
        details["grade"] = "C"
    else:
        details["grade"] = "D"
    
    return {"score": score, "grade": details["grade"], "details": details}
