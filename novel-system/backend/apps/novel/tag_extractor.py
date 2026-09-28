"""Tag auto-extraction (v81) — TF-IDF keyword extraction."""
from collections import Counter
import re


def extract_keywords(text: str, top_n: int = 10) -> list[dict]:
    """Extract top N keywords using simple TF (frequency) + length weighting.
    
    For production, use jieba.analyse.extract_tags() — this is a lightweight fallback.
    """
    if not text:
        return []
    
    # Try jieba first
    try:
        import jieba.analyse
        tags = jieba.analyse.extract_tags(text, topK=top_n, withWeight=True)
        return [{"keyword": t[0], "weight": round(t[1], 4)} for t in tags]
    except ImportError:
        pass
    
    # Fallback: simple bigram frequency
    words = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)
    counts = Counter(words)
    # Weight: frequency × log(length)
    weighted = [(w, c * (1 + 0.1 * len(w))) for w, c in counts.most_common(100)]
    weighted.sort(key=lambda x: -x[1])
    return [{"keyword": w, "weight": round(s, 2)} for w, s in weighted[:top_n]]


def extract_and_assign_tags(book, top_n: int = 5, create_tags: bool = True) -> list[str]:
    """Extract keywords from book intro + first chapter and assign as tags."""
    from apps.novel.models import Tag
    
    text = (book.intro or "")
    first_ch = book.chapters.order_by("order_index").first()
    if first_ch and first_ch.content:
        text += " " + first_ch.content[:2000]
    
    keywords = extract_keywords(text, top_n=top_n)
    tag_names = [k["keyword"] for k in keywords]
    
    if create_tags:
        for name in tag_names:
            tag, created = Tag.objects.get_or_create(name=name, defaults={"is_auto": True})
            book.tags.add(tag)
    
    return tag_names
