"""Log stream (v79) — real-time log push via SSE."""
from __future__ import annotations
import json, time
from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_log_stream(request, task_id: int):
    """SSE stream of task logs — emits new log entries as they arrive."""
    from apps.crawler_tasks.models import CrawlerTaskLog
    def event_stream():
        last_id = 0
        for _ in range(7200):  # 3h max
            new_logs = CrawlerTaskLog.objects.filter(task_id=task_id, id__gt=last_id).order_by("id")
            for log in new_logs:
                last_id = log.id
                data = {"id": log.id, "level": log.level, "message": log.message,
                        "url": log.url, "ts": log.created_at.isoformat()}
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
            time.sleep(2)
    resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp
