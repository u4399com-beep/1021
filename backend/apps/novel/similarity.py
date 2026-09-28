"""Chapter content similarity detection (v85) — prevent duplicate crawl."""
from __future__ import annotations
import hashlib
from difflib import SequenceMatcher

def content_hash(text: str) -> str:
    """SimHash-style content fingerprint (simplified)."""
    if not text: return ""
    # Normalize: strip HTML, lowercase, remove whitespace
    import re
    clean = re.sub(r'<[^>]+>', '', text).lower().replace(' ', '').replace('\n', '')[:2000]
    return hashlib.md5(clean.encode('utf-8')).hexdigest()

def similarity_ratio(text1: str, text2: str) -> float:
    """Compute similarity ratio between two texts (0.0-1.0)."""
    if not text1 or not text2: return 0.0
    # Quick hash check first
    h1, h2 = content_hash(text1), content_hash(text2)
    if h1 == h2: return 1.0
    # Fallback to sequence matching (first 2000 chars for performance)
    return SequenceMatcher(None, text1[:2000], text2[:2000]).ratio()

def is_likely_duplicate(new_content: str, existing_hashes: list[str], threshold: float = 0.85) -> bool:
    """Check if new content is likely a duplicate of existing content."""
    new_hash = content_hash(new_content)
    if new_hash in existing_hashes:
        return True
    # For exact hash match, we're done. For fuzzy, we'd need to compare with each existing.
    return False
