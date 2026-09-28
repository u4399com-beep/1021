"""Health check probe (v97) — deep system health check."""
from __future__ import annotations
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([AllowAny])
def health_probe(request):
    """Deep health probe — checks all critical subsystems."""
    checks = {}
    # DB check
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "fail", "error": str(e)[:100]}
    # Redis check
    try:
        from django.core.cache import cache
        cache.set("health:probe", "ok", timeout=5)
        checks["redis"] = {"status": "ok" if cache.get("health:probe") == "ok" else "fail"}
    except Exception as e:
        checks["redis"] = {"status": "fail", "error": str(e)[:100]}
    # Disk check
    try:
        import shutil
        usage = shutil.disk_usage("/")
        checks["disk"] = {"status": "ok", "percent": round(usage.used / usage.total * 100, 1)}
    except Exception:
        checks["disk"] = {"status": "unknown"}
    # Memory check
    try:
        import psutil
        mem = psutil.virtual_memory()
        checks["memory"] = {"status": "ok" if mem.percent < 90 else "warning", "percent": mem.percent}
    except Exception:
        checks["memory"] = {"status": "unknown"}
    
    all_ok = all(c["status"] == "ok" for c in checks.values())
    return Response({"ok": all_ok, "checks": checks})
