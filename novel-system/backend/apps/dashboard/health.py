"""System health monitoring (v38) — CPU / memory / disk / queue depth.

Provides a single endpoint that returns all key health metrics in one
call — useful for a single-panel monitoring widget in the admin UI.
"""

import os
import platform
import shutil
import time
from typing import Any

import psutil
from django.conf import settings
from django.core.cache import cache
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


def _cpu_usage() -> float:
    """Return CPU usage percentage (0-100)."""
    try:
        return psutil.cpu_percent(interval=0.5)
    except Exception:
        return 0.0


def _memory_usage() -> dict:
    try:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / 1024**3, 2),
            "used_gb": round(mem.used / 1024**3, 2),
            "available_gb": round(mem.available / 1024**3, 2),
            "percent": mem.percent,
        }
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "available_gb": 0, "percent": 0}


def _disk_usage() -> dict:
    try:
        # Use MEDIA_ROOT as the "interesting" disk
        disk_path = str(settings.MEDIA_ROOT)
        usage = shutil.disk_usage(disk_path)
        return {
            "path": disk_path,
            "total_gb": round(usage.total / 1024**3, 2),
            "used_gb": round(usage.used / 1024**3, 2),
            "free_gb": round(usage.free / 1024**3, 2),
            "percent": round(usage.used / usage.total * 100, 1) if usage.total else 0,
        }
    except Exception as e:
        return {"path": "?", "error": repr(e)}


def _queue_depth() -> dict:
    """How many crawler tasks are queued / running / paused."""
    from apps.crawler_tasks.models import CrawlerTask
    return {
        "queued": CrawlerTask.objects.filter(status="queued").count(),
        "running": CrawlerTask.objects.filter(status="running").count(),
        "paused": CrawlerTask.objects.filter(status="paused").count(),
        "error": CrawlerTask.objects.filter(status="error").count(),
    }


def _celery_active_count() -> dict:
    """Inspect Celery active workers + tasks."""
    try:
        from config import celery_app
        inspect = celery_app.control.inspect(timeout=2)
        active = inspect.active() or {}
        workers = list(active.keys())
        total_active = sum(len(tasks) for tasks in active.values())
        return {
            "workers_online": len(workers),
            "worker_names": workers,
            "active_tasks": total_active,
        }
    except Exception as e:
        return {"error": repr(e)}


def _db_connection_check() -> dict:
    """Quick DB ping."""
    from django.db import connection
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            row = cur.fetchone()
        return {"ok": True, "engine": settings.DATABASES["default"]["ENGINE"]}
    except Exception as e:
        return {"ok": False, "error": repr(e)}


def _redis_check() -> dict:
    try:
        cache.set("health:ping", "pong", timeout=10)
        return {"ok": cache.get("health:ping") == "pong"}
    except Exception as e:
        return {"ok": False, "error": repr(e)}


def _uptime() -> float:
    """Process uptime in seconds (best-effort via process start time)."""
    try:
        proc = psutil.Process(os.getpid())
        return time.time() - proc.create_time()
    except Exception:
        return 0.0


def _alert_status(metrics: dict) -> list[dict]:
    """Check critical thresholds and return alert list."""
    alerts = []
    if metrics["cpu_percent"] > 90:
        alerts.append({"level": "danger", "metric": "cpu", "value": metrics["cpu_percent"],
                       "threshold": 90, "message": "CPU 使用率过高"})
    if metrics["memory"]["percent"] > 90:
        alerts.append({"level": "danger", "metric": "memory", "value": metrics["memory"]["percent"],
                       "threshold": 90, "message": "内存使用率过高"})
    if metrics["disk"]["percent"] > 90:
        alerts.append({"level": "danger", "metric": "disk", "value": metrics["disk"]["percent"],
                       "threshold": 90, "message": "磁盘空间不足"})
    if metrics["queue"]["error"] > 10:
        alerts.append({"level": "warning", "metric": "queue_errors", "value": metrics["queue"]["error"],
                       "threshold": 10, "message": "失败任务过多"})
    if metrics["queue"]["queued"] > 50:
        alerts.append({"level": "warning", "metric": "queue_depth", "value": metrics["queue"]["queued"],
                       "threshold": 50, "message": "任务积压"})
    if not metrics["db"]["ok"]:
        alerts.append({"level": "danger", "metric": "db", "message": "数据库连接失败"})
    if not metrics["redis"]["ok"]:
        alerts.append({"level": "danger", "metric": "redis", "message": "Redis 连接失败"})
    return alerts


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def system_health(request):
    """Single endpoint returning all system health metrics.

    Response:
        {
          "hostname": str,
          "platform": str,
          "python_version": str,
          "uptime_seconds": float,
          "cpu_percent": float,
          "memory": {...},
          "disk": {...},
          "queue": {...},
          "celery": {...},
          "db": {...},
          "redis": {...},
          "alerts": [...],
          "ts": ISO timestamp
        }
    """
    metrics = {
        "hostname": platform.node(),
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "python_version": platform.python_version(),
        "uptime_seconds": round(_uptime(), 1),
        "cpu_percent": _cpu_usage(),
        "memory": _memory_usage(),
        "disk": _disk_usage(),
        "queue": _queue_depth(),
        "celery": _celery_active_count(),
        "db": _db_connection_check(),
        "redis": _redis_check(),
    }
    metrics["alerts"] = _alert_status(metrics)
    metrics["ts"] = time.time()
    return Response(metrics)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def quick_health(request):
    """Lightweight endpoint suitable for /health on load balancers.

    Returns: {ok: bool, db_ok: bool, redis_ok: bool}
    """
    db_ok = _db_connection_check()["ok"]
    redis_ok = _redis_check()["ok"]
    return Response({
        "ok": db_ok and redis_ok,
        "db_ok": db_ok,
        "redis_ok": redis_ok,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_health(request):
    """Public health check (no auth) for Docker HEALTHCHECK / load balancer."""
    return Response({"ok": True, "service": "novel-system"})
