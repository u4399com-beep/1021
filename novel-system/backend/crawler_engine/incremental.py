"""Incremental update + resume (v140) — detect new chapters + resume from checkpoint."""
from __future__ import annotations
from typing import Any
from django.core.cache import cache
from loguru import logger


def get_checkpoint(task_id: int) -> dict:
    """Get the resume checkpoint for a task."""
    return cache.get(f"task_checkpoint:{task_id}", {}) or {}


def save_checkpoint(task_id: int, checkpoint: dict) -> None:
    """Save checkpoint for resume on next run."""
    cache.set(f"task_checkpoint:{task_id}", checkpoint, timeout=7 * 24 * 3600)  # 7 days


def clear_checkpoint(task_id: int) -> None:
    """Clear checkpoint after successful completion."""
    cache.delete(f"task_checkpoint:{task_id}")


def detect_new_chapters_from_toc(book, toc_chapters: list[dict]) -> dict:
    """Compare TOC chapters with existing chapters in DB.
    
    Returns: {new_urls, existing_urls, new_count, existing_count}
    """
    existing_urls = set(book.chapters.values_list("source_url", flat=True))
    existing_titles = set(book.chapters.values_list("title", flat=True))
    
    new = []
    existing = []
    for ch in toc_chapters:
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
        "new_count": len(new),
        "existing_count": len(existing),
        "total_toc": len(toc_chapters),
    }


def resume_from_checkpoint(task_id: int, all_urls: list[str]) -> list[str]:
    """Filter URL list to resume from last checkpoint.
    
    If checkpoint has last_completed_url, skip all URLs before it.
    """
    cp = get_checkpoint(task_id)
    last_url = cp.get("last_completed_url", "")
    if not last_url:
        return all_urls
    
    try:
        idx = all_urls.index(last_url)
        return all_urls[idx + 1:]  # resume from next URL after last completed
    except ValueError:
        return all_urls  # last URL not in list, start from beginning


def update_checkpoint(task_id: int, completed_url: str) -> None:
    """Update checkpoint with the latest completed URL."""
    cp = get_checkpoint(task_id)
    cp["last_completed_url"] = completed_url
    cp["completed_count"] = cp.get("completed_count", 0) + 1
    save_checkpoint(task_id, cp)
