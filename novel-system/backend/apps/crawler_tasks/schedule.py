"""Schedule helpers for CrawlerTask.

We use django_celery_beat's CrontabSchedule + PeriodicTask to schedule
crawler tasks via the standard celery beat mechanism.

A CrawlerTask with `schedule_enabled=True` and `schedule_cron='0 3 * * *'`
produces (or updates) a corresponding CrontabSchedule + PeriodicTask, and
the beat scheduler will fire `apps.crawler_tasks.tasks.run_crawler_task`
with the task id at the scheduled time.
"""

import re

from django.utils import timezone
from loguru import logger

# Standard 5-segment cron regex (very permissive; we accept *, numbers, ranges, lists, steps)
_CRON_RE = re.compile(
    r"^\s*"
    r"(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)"
    r"\s*$"
)


class CronValidationError(Exception):
    pass


def validate_cron(expr: str) -> None:
    """Raise CronValidationError if `expr` is not a valid 5-segment cron string."""
    if not expr or not expr.strip():
        raise CronValidationError("cron 表达式不能为空")
    m = _CRON_RE.match(expr)
    if not m:
        raise CronValidationError(f"cron 表达式格式错误: {expr!r}，应为 5 段: 'minute hour day month weekday'")
    for seg in m.groups():
        if not re.match(r"^[*/,\-0-9LW#]+$", seg):
            raise CronValidationError(f"cron 字段非法: {seg!r}")


def parse_cron_to_crontab(expr: str):
    """Parse a 5-segment cron expression into django_celery_beat CrontabSchedule kwargs.

    Returns: dict suitable for CrontabSchedule.objects.get_or_create(**kwargs)
    """
    validate_cron(expr)
    m = _CRON_RE.match(expr).groups()
    minute, hour, day_of_month, month_of_year, day_of_week = m

    def _normalize(s: str) -> str:
        # django_celery_beat doesn't accept '*' as is for some fields? Actually it does,
        # but for clarity we keep it as-is and let CrontabSchedule validate.
        return s.strip()

    return {
        "minute": _normalize(minute),
        "hour": _normalize(hour),
        "day_of_month": _normalize(day_of_month),
        "month_of_year": _normalize(month_of_year),
        "day_of_week": _normalize(day_of_week),
    }


def sync_schedule(task):
    """Create or update the django_celery_beat PeriodicTask for this CrawlerTask.

    Returns the (crontab, periodic_task) tuple.
    """
    from django_celery_beat.models import CrontabSchedule, PeriodicTask

    if not task.schedule_enabled or not task.schedule_cron:
        # Disabled: remove any existing periodic task
        PeriodicTask.objects.filter(
            name=f"crawler_task_{task.id}",
            task="apps.crawler_tasks.tasks.run_crawler_task",
        ).delete()
        task.schedule_next_run = None
        task.save(update_fields=["schedule_next_run"])
        return None, None

    # Validate cron first
    try:
        cron_kwargs = parse_cron_to_crontab(task.schedule_cron)
    except CronValidationError as e:
        logger.error(f"task {task.id} invalid cron '{task.schedule_cron}': {e}")
        PeriodicTask.objects.filter(
            name=f"crawler_task_{task.id}",
        ).update(enabled=False)
        return None, None

    # Find existing CrontabSchedule or create one
    crontab, _ = CrontabSchedule.objects.get_or_create(
        timezone=timezone.get_current_timezone_name(),
        defaults=cron_kwargs,
    )
    # Update fields if cron expr changed
    changed = False
    for k, v in cron_kwargs.items():
        if getattr(crontab, k) != v:
            setattr(crontab, k, v)
            changed = True
    if changed:
        crontab.save()

    # Create or update the PeriodicTask
    periodic_task, created = PeriodicTask.objects.update_or_create(
        name=f"crawler_task_{task.id}",
        defaults={
            "task": "apps.crawler_tasks.tasks.run_crawler_task",
            "crontab": crontab,
            "enabled": task.schedule_enabled and task.enabled,
            "args": f"[{task.id}]",
            "kwargs": "{}",
            "description": f"Auto-scheduled crawler task: {task.name}",
        },
    )

    # Compute next run time
    if periodic_task.enabled:
        # django_celery_beat computes this on save; refresh from DB
        periodic_task.refresh_from_db()
        task.schedule_next_run = periodic_task.last_run_at or None
    else:
        task.schedule_next_run = None
    task.save(update_fields=["schedule_next_run"])

    return crontab, periodic_task


def disable_schedule(task):
    """Disable scheduling for a task (does not delete the cron for audit)."""
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(
        name=f"crawler_task_{task.id}",
        task="apps.crawler_tasks.tasks.run_crawler_task",
    ).update(enabled=False)
    task.schedule_enabled = False
    task.schedule_next_run = None
    task.save(update_fields=["schedule_enabled", "schedule_next_run"])


def record_run(task):
    """Call after a scheduled run completes to update counters."""
    task.schedule_run_count = (task.schedule_run_count or 0) + 1
    task.schedule_last_run = timezone.now()

    # If we've hit max_runs, auto-disable
    if task.schedule_max_runs > 0 and task.schedule_run_count >= task.schedule_max_runs:
        task.schedule_enabled = False
        disable_schedule(task)

    task.save(update_fields=["schedule_run_count", "schedule_last_run", "schedule_enabled"])
