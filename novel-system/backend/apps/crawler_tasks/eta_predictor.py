"""Execution time prediction (v58) — estimate how long a task will take."""
from datetime import timedelta
from django.utils import timezone
from .models import CrawlerTask


def predict_eta(task: CrawlerTask) -> dict:
    """Predict how long a task will take based on historical data.
    
    Returns: {estimated_seconds, estimated_finish, confidence}
    """
    # Find similar completed tasks (same source)
    similar = CrawlerTask.objects.filter(
        list_rule__source=task.list_rule.source if task.list_rule else None,
        status="done",
        finished_at__isnull=False,
        started_at__isnull=False,
    )
    if not similar.exists():
        # Fallback: rough estimate based on URL count
        url_count = len(task.target_urls or []) + len(task.url_range.get("template", "") and [1] or [])
        est_per_url = 3.0  # 3 seconds per URL (average)
        est_seconds = url_count * est_per_url
        return {
            "estimated_seconds": int(est_seconds),
            "estimated_finish": (timezone.now() + timedelta(seconds=est_seconds)).isoformat(),
            "confidence": "low (no historical data)",
            "basis": f"{url_count} URLs × {est_per_url}s/url",
        }
    
    # Calculate average duration
    durations = []
    for t in similar[:20]:
        if t.started_at and t.finished_at:
            dur = (t.finished_at - t.started_at).total_seconds()
            durations.append(dur)
    
    if not durations:
        return {"estimated_seconds": 0, "confidence": "no_data"}
    
    avg = sum(durations) / len(durations)
    # Adjust by URL count ratio
    if task.total_items and similar.first().total_items:
        ratio = task.total_items / similar.first().total_items
        est = avg * ratio
    else:
        est = avg
    
    return {
        "estimated_seconds": int(est),
        "estimated_finish": (timezone.now() + timedelta(seconds=est)).isoformat(),
        "confidence": f"medium (based on {len(durations)} similar tasks)",
        "avg_historical_seconds": int(avg),
    }
