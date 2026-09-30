"""Advanced dedup engine (v206) — multiple dedup strategies."""
import hashlib


def content_fingerprint(content: str) -> str:
    """SHA-256 fingerprint of normalized content."""
    import re
    clean = re.sub(r'<[^>]+>', '', content).lower().replace(' ', '').replace('\n', '')[:2000]
    return hashlib.sha256(clean.encode()).hexdigest()


def title_fingerprint(title: str) -> str:
    """Normalized title fingerprint."""
    return hashlib.sha256(title.strip().lower().encode()).hexdigest()


def is_duplicate_content(new_content: str, existing_hashes: set) -> bool:
    """Check if content hash matches any existing."""
    return content_fingerprint(new_content) in existing_hashes


def is_duplicate_chapter(title: str, url: str, existing_titles: set, existing_urls: set) -> bool:
    """Check if chapter is duplicate by URL or title."""
    return url in existing_urls or title.strip().lower() in {t.lower() for t in existing_titles}
