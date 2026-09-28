"""Auto priority adjustment (v64) — boost task priority based on queue depth."""
from __future__ import annotations
from django.db.models import Count, Q
from .models import CrawlerTask


def adjust_priorities() -> dict:
    """Scan all queued tasks and auto-adjust priority based on age + queue depth.
    
    Rules:
      - Tasks in queue > 10 minutes get +10 priority
      - Tasks in queue > 30 minutes get +20 priority  
      - Tasks in queue > 60 minutes get +30 priority
      - Max cap: 100
    """
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    adjusted = []
    queued = CrawlerTask.objects.filter(status="queued")
    for task in queued:
        if not task.started_at:
            continue
        age = (now - task.started_at).total_seconds()
        boost = 0
        if age > 3600:
            boost = 30
        elif age > 1800:
            boost = 20
        elif age > 600:
            boost = 10
        if boost > 0:
            new_priority = min(100, (task.priority or 50) + boost)
            if new_priority != task.priority:
                task.priority = new_priority
                task.save(update_fields=["priority"])
                adjusted.append({
                    "task_id": task.id, "name": task.name,
                    "old_priority": task.priority - boost,
                    "new_priority": new_priority,
                    "age_minutes": round(age / 60, 1),
                })
    return {"adjusted": adjusted, "count": len(adjusted)}
