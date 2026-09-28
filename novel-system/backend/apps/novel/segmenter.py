"""Content auto-segmentation (v61) — split long chapters into readable segments."""
import re


def segment_content(content: str, max_chars: int = 3000) -> list[str]:
    """Split content into segments of at most max_chars, on paragraph boundaries."""
    if not content or len(content) <= max_chars:
        return [content] if content else []
    
    # Try paragraph boundaries first
    paragraphs = re.split(r"(\n\n|<br\s*/?>|</p>)", content)
    segments = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) <= max_chars:
            current += para
        else:
            if current:
                segments.append(current)
            current = para
    if current:
        segments.append(current)
    
    # If any segment is still too long, hard-split
    final = []
    for seg in segments:
        while len(seg) > max_chars:
            final.append(seg[:max_chars])
            seg = seg[max_chars:]
        if seg:
            final.append(seg)
    
    return final


def segment_stats(content: str, max_chars: int = 3000) -> dict:
    """Return segmentation statistics without actually segmenting."""
    total = len(content or "")
    est_segments = max(1, (total + max_chars - 1) // max_chars)
    return {
        "total_chars": total,
        "max_chars_per_segment": max_chars,
        "estimated_segments": est_segments,
    }
