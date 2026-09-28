"""Chapter update detection (v65) — detect new chapters for incremental updates."""
from .models import Book, Chapter


def detect_new_chapters(book: Book, remote_chapters: list[dict]) -> dict:
    """Compare remote chapter list with local chapters.
    
    Args:
        book: the book to check
        remote_chapters: list of {url, title} from the TOC parser
    
    Returns: {new: [...], existing: [...], total_remote, total_local}
    """
    existing_urls = set(book.chapters.values_list("source_url", flat=True))
    existing_titles = set(book.chapters.values_list("title", flat=True))
    
    new = []
    existing = []
    for ch in remote_chapters:
        url = ch.get("url", "")
        title = ch.get("title", "")
        if url and url in existing_urls:
            existing.append(ch)
        elif title and title in existing_titles:
            existing.append(ch)
        else:
            new.append(ch)
    
    return {
        "new": new,
        "existing": existing,
        "total_remote": len(remote_chapters),
        "total_local": book.chapters.count(),
        "new_count": len(new),
    }
