"""Backup views — manual trigger + diagnostics."""
from __future__ import annotations

from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.account.permissions import CanEditSystem

from .backup_engine import diagnostics, run_backup


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def backup_status(request):
    """Check backup configuration."""
    return Response(diagnostics())


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, CanEditSystem])
def trigger_backup(request):
    """Manually trigger a full backup right now.

    Returns the backup report dict.
    """
    try:
        report = run_backup()
        return Response(report)
    except Exception as e:
        return Response({"error": repr(e)}, status=500)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_backups(request):
    """List backup files in the backup directory."""
    from pathlib import Path
    from .backup_engine import get_backup_dir
    backup_dir = get_backup_dir()
    files = []
    for p in backup_dir.iterdir():
        if p.is_file():
            files.append({
                "name": p.name,
                "size_bytes": p.stat().st_size,
                "size_mb": round(p.stat().st_size / 1024 / 1024, 2),
                "mtime": p.stat().st_mtime,
            })
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return Response({"backups": files, "count": len(files)})
