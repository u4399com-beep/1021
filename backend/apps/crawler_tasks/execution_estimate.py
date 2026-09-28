"""Execution estimate (v95) — estimate task duration."""
from __future__ import annotations

def estimate_execution(url_count: int, avg_seconds_per_url: float = 3.0,
                       threads_max: int = 5) -> dict:
    """Estimate total execution time."""
    total_seconds = (url_count * avg_seconds_per_url) / max(1, threads_max)
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return {
        "url_count": url_count, "avg_seconds_per_url": avg_seconds_per_url,
        "threads": threads_max,
        "estimated_seconds": int(total_seconds),
        "estimated_human": f"{hours}h{minutes}m" if hours else f"{minutes}m",
    }
