"""Server-Sent Events (SSE) for real-time task progress (v35).

Provides a streaming endpoint that the frontend can subscribe to for
live updates of crawler task progress.

Endpoint:
  GET /api/v1/tasks/{id}/progress-stream/

Sends a `data:` line every ~1.5 seconds containing the current progress.
"""

import json
import time

from django.http import StreamingHttpResponse, HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes


def _sse_event(data: dict) -> bytes:
    """Format a dict as an SSE event payload."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def _build_progress_dict(task):
    return {
        "task_id": task.id,
        "name": task.name,
        "status": task.status,
        "total": task.total_items,
        "processed": task.processed_items,
        "success": task.success_items,
        "failed": task.failed_items,
        "skipped": task.skipped_items,
        "priority": task.priority,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "elapsed_seconds": (
            (task.finished_at or _now()).timestamp() - task.started_at.timestamp()
        ) if task.started_at else 0,
        "ts": _now().isoformat(),
    }


def _now():
    from django.utils import timezone
    return timezone.now()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def progress_stream(request, task_id: int):
    """SSE stream: emit progress every 1.5s for the given task.

    Client-side usage (JavaScript EventSource):
        const es = new EventSource('/api/v1/tasks/5/progress-stream/');
        es.onmessage = e => {
            const d = JSON.parse(e.data);
            console.log(d.status, d.processed + '/' + d.total);
        };

    When the task is done/error/stopped, sends a final event and closes.
    """
    from apps.crawler_tasks.models import CrawlerTask

    def event_stream():
        last_status = None
        for i in range(7200):  # cap at 7200 × 1.5s = 3h
            try:
                task = CrawlerTask.objects.filter(pk=task_id).first()
                if not task:
                    yield _sse_event({"error": "task not found", "task_id": task_id})
                    return
                data = _build_progress_dict(task)
                yield _sse_event(data)
                # Close when task is terminal
                if task.status in ("done", "error", "stopped"):
                    yield _sse_event({"event": "closed", "reason": task.status})
                    return
            except Exception as e:
                yield _sse_event({"error": repr(e)})
                return
            time.sleep(1.5)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # Disable nginx buffering
    response["Connection"] = "keep-alive"
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def all_progress_stream(request):
    """SSE stream: emit progress for ALL running tasks every 2s.

    Each event is wrapped as {type: "task_progress", task_id, ...}.
    Useful for the dashboard widget showing all running tasks.
    """
    from apps.crawler_tasks.models import CrawlerTask

    def event_stream():
        for i in range(3600):
            try:
                running = CrawlerTask.objects.filter(status="running")
                events = [_build_progress_dict(t) for t in running]
                yield _sse_event({
                    "type": "running_tasks_snapshot",
                    "tasks": events,
                    "count": len(events),
                    "ts": _now().isoformat(),
                })
            except Exception as e:
                yield _sse_event({"error": repr(e)})
                return
            time.sleep(2)

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"
    return response
