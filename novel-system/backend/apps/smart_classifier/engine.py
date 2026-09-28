"""智能分类引擎。

策略：
1. 用 jieba 对标题+简介+前几章内容做关键词提取
2. 命中 CategoryKeyword 表的关键词则计入权重
3. 取前 N 个权重最高的分类
4. 完结判断：匹配 FinishedPattern 表的正则
"""

import re

from .models import CategoryKeyword, FinishedPattern


def _tokenize(text: str) -> list[str]:
    try:
        import jieba  # noqa
        return list(jieba.cut_for_search(text or ""))
    except Exception:
        # fallback: simple split
        return re.findall(r"[\w]+", text or "", flags=re.UNICODE)


def classify_book(title: str, intro: str = "", chapter_snippet: str = "", top_n: int = 3, book_id: int | None = None) -> list[dict]:
    """返回 [{name, weight, score}, ...]"""
    text = " ".join([title or "", intro or "", chapter_snippet or ""])[:5000]
    tokens = _tokenize(text)
    if not tokens:
        return []

    # keyword hit count
    hits: dict[str, float] = {}
    hit_kw_objs = []
    for kw in CategoryKeyword.objects.all():
        for token in tokens:
            if kw.keyword in token or token in kw.keyword:
                hits[kw.category_name] = hits.get(kw.category_name, 0) + kw.weight
                hit_kw_objs.append(kw)

    # Record hit statistics (one DB write per matched keyword)
    if book_id is not None and hit_kw_objs:
        for kw in hit_kw_objs:
            try:
                kw.record_hit(book_id=book_id)
            except Exception:
                pass

    if not hits:
        return []

    total = sum(hits.values()) or 1.0
    ranked = sorted(hits.items(), key=lambda x: -x[1])[:top_n]
    return [{"name": name, "weight": w, "score": round(w / total, 4)} for name, w in ranked]


def detect_finished(title: str, intro: str = "", last_chapter_title: str = "") -> bool:
    """检测是否已完结。

    匹配 FinishedPattern 表里的正则。
    """
    text = " ".join([title or "", intro or "", last_chapter_title or ""])
    matched_patterns = []
    for p in FinishedPattern.objects.filter(enabled=True).order_by("priority"):
        try:
            if re.search(p.pattern, text, flags=re.IGNORECASE):
                matched_patterns.append(p)
        except re.error:
            continue

    # Record hit stats for matched patterns
    for p in matched_patterns:
        try:
            p.record_hit()
        except Exception:
            pass

    return bool(matched_patterns)
