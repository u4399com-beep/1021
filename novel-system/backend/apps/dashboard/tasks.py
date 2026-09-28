"""Celery tasks for periodic backups (v37).

Schedule via Celery beat:
    30 3 * * *  → apps.dashboard.tasks.run_daily_backup

Configure via django_celery_beat admin or django-celery-beat PeriodicTask.
"""

from loguru import logger

from config import celery_app


@celery_app.task(name="apps.dashboard.tasks.run_daily_backup")
def run_daily_backup():
    """Daily backup at 03:30 — invoked by celery beat.

    Skipped when BACKUP_ENABLED is False.
    """
    from .backup_engine import is_backup_enabled, run_backup
    if not is_backup_enabled():
        logger.info("daily backup skipped — BACKUP_ENABLED=False")
        return {"skipped": True, "reason": "BACKUP_ENABLED=False"}
    try:
        report = run_backup()
        # Send webhook notification
        try:
            from apps.webhooks.engine import dispatch_event
            dispatch_event("system.error" if report.get("s3_url") is None and not report.get("archive_path") else "task.done", {
                "name": "daily-backup",
                "success": 1,
                "failed": 0,
                "skipped": 0,
                "details": report,
            })
        except Exception:
            pass
        return report
    except Exception as e:
        logger.error(f"daily backup failed: {e!r}")
        return {"error": repr(e)}


@celery_app.task(name="apps.dashboard.tasks.cleanup_old_backups")
def cleanup_old_backups_task():
    """Standalone cleanup — run weekly."""
    from .backup_engine import cleanup_old_backups
    deleted = cleanup_old_backups(retention_days=30)
    return {"deleted": deleted}
