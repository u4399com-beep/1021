"""Pseudo-original rewriting engine.

Goal: take a paragraph of text, produce a different paragraph that means the
same thing but uses different words / sentence order / filler. Each rewrite is
tracked so the same input never produces the same output twice.

Layers:
  1. synonym_replace: replace words using the Synonym table
  2. sentence_reorder: split paragraph into sentences, reorder clause-joined ones
  3. interference_insert: append random interference sentences from the
     InterferenceSentence table

Uniqueness:
  - Each rewrite records (original_hash, transformations) to a RewriteRecord
  - Before rewriting, we check which transformations have been applied before
    to this exact original_hash and avoid repeating them.
"""
from __future__ import annotations

import hashlib
import random
import re
from typing import Any

from .models import InterferenceSentence, RewriteRecord, Synonym


# Default seed synonyms — only loaded if Synonym table is empty
DEFAULT_SYNONYMS = {
    "他": ["这人", "此人", "对方"],
    "她": ["这人", "此人", "对方"],
    "看": ["望", "瞧", "盯", "望向"],
    "走": ["行", "踱", "迈步", "走动"],
    "说": ["道", "言", "开口", "说道"],
    "想": ["思忖", "心想", "思", "盘算"],
    "笑": ["微笑", "嘴角上扬", "展颜"],
    "哭": ["流泪", "落泪", "哽咽"],
    "好": ["不错", "甚佳", "极佳"],
    "坏": ["差", "不佳", "糟糕"],
    "大": ["宏大", "巨大", "庞大"],
    "小": ["微小", "细小", "袖珍"],
    "很": ["非常", "极其", "十分"],
    "都": ["皆", "俱", "全"],
    "和": ["与", "同", "及"],
    "或": ["或许", "抑或", "或者"],
    "因为": ["由于", "因", "盖因"],
    "所以": ["因此", "故而", "是以"],
    "但是": ["然而", "不过", "只是"],
    "如果": ["倘若", "若是", "假如"],
    "可以": ["能够", "得以", "可"],
    "已经": ["已然", "业已", "早已"],
    "突然": ["忽然", "陡然", "蓦地"],
    "迅速": ["快速", "迅捷", "疾速"],
    "知道": ["晓得", "知晓", "明白"],
    "开始": ["起初", "起先", "始而"],
    "结束": ["完结", "终结", "终了"],
    "美丽": ["漂亮", "标致", "俊美"],
    "强大": ["强横", "强悍", "威猛"],
    "弱小": ["孱弱", "羸弱", "纤弱"],
    "勇敢": ["果敢", "勇猛", "勇毅"],
    "聪明": ["机敏", "智慧", "睿智"],
    "愚蠢": ["愚笨", "愚钝", "木讷"],
}

DEFAULT_INTERFERENCES = [
    "风从远处吹来，带着一丝不易察觉的凉意。",
    "周遭安静得仿佛能听见自己的心跳。",
    "光线斜斜地照进窗户，将一切染上一层淡金色。",
    "时间仿佛在那一刻凝固了。",
    "远处的山影在云雾间若隐若现。",
    "没有人开口，空气里弥漫着一种说不出的张力。",
    "呼吸间，似乎有什么东西正在悄然改变。",
    "天空泛着微弱的青蓝色，像一幅未完成的水墨画。",
    "脚步声在空旷的走廊里回响着。",
    "视线所及之处，皆是寂静无声的灰白。",
]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------
# Layer 1 — synonym replacement
# ------------------------------------------------------------------
def synonym_replace(text: str, *, density: float = 0.4, seed: int | None = None,
                     avoid: set[str] | None = None) -> tuple[str, list[str]]:
    """Replace words with synonyms from the DB-backed dictionary.

    Args:
        text: input paragraph
        density: 0.0~1.0, per-word replacement probability
        seed: optional random seed
        avoid: set of original->synonym pair strings to skip (used to avoid duplicates)

    Returns: (rewritten_text, list_of_transformations)
    """
    if not text:
        return text, []
    if seed is not None:
        random.seed(seed)

    # Load synonyms from DB, falling back to DEFAULT_SYNONYMS
    syn_map: dict[str, list[str]] = {}
    qs = Synonym.objects.filter(enabled=True)
    if not qs.exists():
        syn_map = DEFAULT_SYNONYMS
    else:
        for s in qs:
            syn_map[s.word] = list(s.synonyms or [])

    transformations: list[str] = []
    out = text
    for word, syns in syn_map.items():
        # Build regex for whole-word match (CJK doesn't have word boundaries,
        # so we just do plain substring match)
        # Use re.sub with a function that picks a synonym with density probability
        def _repl(m, w=word, s=syns):
            if random.random() >= density:
                return m.group(0)
            # Avoid used synonyms
            available = [x for x in s if f"{w}->{x}" not in (avoid or set())] or s
            if not available:
                return m.group(0)
            choice = random.choice(available)
            transformations.append(f"synonym:{w}->{choice}")
            return choice

        out = re.sub(re.escape(word), _repl, out)

    return out, transformations


# ------------------------------------------------------------------
# Layer 2 — sentence reordering
# ------------------------------------------------------------------
_CLAUSE_SPLITTERS = re.compile(r"[，,、；;]")


def sentence_reorder(text: str, *, seed: int | None = None) -> tuple[str, list[str]]:
    """Split sentences by clause delimiters and reorder some clauses.

    Only swaps adjacent clauses of equal length to preserve readability.
    """
    if not text:
        return text, []
    if seed is not None:
        random.seed(seed)

    # Split by sentence first
    sentences = re.split(r"([。！？\?\!\n])", text)
    # Re-group sentences with their endings
    out_parts = []
    transformations = []
    i = 0
    while i < len(sentences):
        sent = sentences[i]
        ending = sentences[i + 1] if i + 1 < len(sentences) else ""
        # Split sentence by clause delimiters
        clauses = re.split(r"([，,、；;])", sent)
        # clauses is now [text, delim, text, delim, text, ...]
        if len(clauses) >= 5 and random.random() < 0.4:
            # Try swapping two adjacent text-clauses (skipping delimiters)
            text_clauses = clauses[::2]
            delim_clauses = clauses[1::2]
            # Pick a random pair to swap
            j = random.randint(0, len(text_clauses) - 2)
            if abs(len(text_clauses[j]) - len(text_clauses[j + 1])) <= 2:
                text_clauses[j], text_clauses[j + 1] = text_clauses[j + 1], text_clauses[j]
                transformations.append(f"reorder:clause@{j}")
                # Reassemble
                new_sent = ""
                for k, tc in enumerate(text_clauses):
                    new_sent += tc
                    if k < len(delim_clauses):
                        new_sent += delim_clauses[k]
                out_parts.append(new_sent + ending)
            else:
                out_parts.append(sent + ending)
        else:
            out_parts.append(sent + ending)
        i += 2

    return "".join(out_parts), transformations


# ------------------------------------------------------------------
# Layer 3 — interference sentence insertion
# ------------------------------------------------------------------
def interference_insert(
    text: str,
    *,
    density: float = 0.3,
    seed: int | None = None,
    avoid_ids: set[int] | None = None,
) -> tuple[str, list[str]]:
    """Append a random interference sentence from the DB-backed pool.

    Avoids repeating the same sentence id within the same render.
    """
    if not text:
        return text, []
    if seed is not None:
        random.seed(seed)

    if random.random() > density:
        return text, []

    # Load from DB or use defaults
    qs = InterferenceSentence.objects.filter(enabled=True)
    if qs.exists():
        # Weight by `weight` field; exclude already-used ids
        candidates = list(qs)
        if avoid_ids:
            candidates = [c for c in candidates if c.id not in avoid_ids]
        if not candidates:
            return text, []
        # Weighted random choice
        weights = [c.weight for c in candidates]
        chosen = random.choices(candidates, weights=weights, k=1)[0]
        sentence = chosen.text
        chosen.used_count += 1
        chosen.save(update_fields=["used_count"])
        transformations = [f"interference:id={chosen.id}"]
    else:
        sentence = random.choice(DEFAULT_INTERFERENCES)
        transformations = [f"interference:default"]

    # Append as a new paragraph or merge with last paragraph
    if text.endswith("\n"):
        return text + sentence + "\n", transformations
    if text.endswith("。") or text.endswith("！") or text.endswith("？"):
        return text + sentence, transformations
    return text + " " + sentence, transformations


# ------------------------------------------------------------------
# Master — rewrite pipeline with dedup tracking
# ------------------------------------------------------------------
def rewrite_paragraph(
    text: str,
    *,
    site=None, book=None, chapter=None,
    synonym: bool = True,
    reorder: bool = True,
    interference: bool = True,
    synonym_density: float = 0.4,
    interference_density: float = 0.3,
    seed: int | None = None,
) -> str:
    """Rewrite a paragraph with all enabled layers, ensuring no two rewrites
    produce the same output for the same input on the same site/book/chapter.
    """
    if not text:
        return text

    # Compute original hash
    original_hash = _hash_text(text)

    # Find which transformations have been applied before to this exact text
    avoid_synonyms: set[str] = set()
    avoid_interference_ids: set[int] = set()
    if synonym or interference:
        existing = RewriteRecord.objects.filter(original_hash=original_hash)
        if site is not None:
            existing = existing.filter(site=site)
        if book is not None:
            existing = existing.filter(book=book)
        for r in existing:
            for t in r.transformations or []:
                if t.startswith("synonym:"):
                    avoid_synonyms.add(t.removeprefix("synonym:"))
                elif t.startswith("interference:id="):
                    try:
                        avoid_interference_ids.add(int(t.removeprefix("interference:id=")))
                    except ValueError:
                        pass

    if seed is not None:
        random.seed(seed)
    actual_seed = random.randint(0, 2**32 - 1)

    out = text
    all_transforms: list[str] = []

    if synonym:
        out, ts = synonym_replace(out, density=synonym_density,
                                   seed=actual_seed, avoid=avoid_synonyms)
        all_transforms.extend(ts)

    if reorder:
        out, ts = sentence_reorder(out, seed=actual_seed + 1)
        all_transforms.extend(ts)

    if interference:
        out, ts = interference_insert(out, density=interference_density,
                                       seed=actual_seed + 2,
                                       avoid_ids=avoid_interference_ids)
        all_transforms.extend(ts)

    # Record this rewrite
    rewritten_hash = _hash_text(out)
    RewriteRecord.objects.create(
        original_hash=original_hash,
        rewritten_hash=rewritten_hash,
        transformations=all_transforms,
        site=site, book=book, chapter=chapter,
    )

    return out


def rewrite_html_content(
    html: str,
    *,
    site=None, book=None, chapter=None,
    synonym: bool = True,
    reorder: bool = True,
    interference: bool = True,
    synonym_density: float = 0.4,
    interference_density: float = 0.3,
    seed: int | None = None,
) -> str:
    """Rewrite only the visible text in HTML, leaving tags/attributes intact."""
    if not html:
        return html

    # Split HTML into "in-tag" and "text" segments using a simple regex
    parts = re.split(r"(<[^>]+>)", html)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 1:
            out.append(p)  # in-tag — keep as-is
        else:
            rewritten = rewrite_paragraph(
                p,
                site=site, book=book, chapter=chapter,
                synonym=synonym, reorder=reorder, interference=interference,
                synonym_density=synonym_density,
                interference_density=interference_density,
                seed=seed,
            )
            out.append(rewritten)
    return "".join(out)
