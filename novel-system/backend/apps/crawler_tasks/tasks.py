"""Celery tasks for the crawler.

This is the orchestration layer:
1. Resolve the list of URLs to crawl (single / range / paginated).
2. For each URL: fetch → parse → store, with dedup + clean + smart-classify.
3. Honor the task lifecycle (pause / stop / dynamic params).
4. Multi-threading via Celery's group / chord (worker concurrency handled by Celery).

The actual fetch + parse logic lives in `crawler_engine.fetcher` and
`crawler_engine.parsers`. This file wires them into a Celery pipeline.
"""

import random
import time
from typing import Any

from celery import group
from celery.exceptions import SoftTimeLimitExceeded
from celery.result import allow_join_result
from loguru import logger

from apps.crawler_tasks.models import CrawlerTask, CrawlerTaskLog
from apps.novel.models import Author, Book, Chapter
from apps.smart_classifier.engine import classify_book, detect_finished

from config import celery_app


@celery_app.task(
    bind=True,
    name="apps.crawler_tasks.tasks.run_crawler_task",
    autoretry_for=(SoftTimeLimitExceeded,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 1},
)
def run_crawler_task(self, task_id: int):
    """Main entry point — runs the full crawler pipeline.

    Acquires a concurrency slot first; if no slot is available, the task
    is re-queued with a short delay (max 3 retries, then marked as 'queued').
    """
    task = CrawlerTask.objects.filter(pk=task_id).first()
    if not task:
        logger.warning(f"crawler task {task_id} not found")
        return

    if not task.enabled:
        logger.info(f"crawler task {task_id} disabled, skip")
        return

    # Concurrency control — try to acquire a slot
    from .concurrency import acquire_slot, release_slot
    if not acquire_slot(task):
        # No slot available — re-queue with 30s delay
        logger.info(f"task {task_id} waiting for concurrency slot")
        run_crawler_task.apply_async(args=[task_id], countdown=30)
        return

    try:
        _execute_task(self, task)
    finally:
        release_slot(task)


def _execute_task(self, task):
    """Actually run the crawler pipeline."""
    # Build URL list
    try:
        urls = _build_urls(task)
        task.total_items = len(urls)
        task.mark_running(self.request.id)
        _log(task, f"start: total={len(urls)} mode={task.mode} priority={task.priority}")
    except Exception as e:
        task.mark_error(repr(e))
        logger.exception(f"task {task.id} prepare error")
        try:
            from .schedule import record_run
            record_run(task)
        except Exception:
            pass
        # v29: try retry if applicable
        _maybe_schedule_retry(task, repr(e))
        return

    # Dispath with a Celery group — each URL becomes a child task
    # Concurrency is bounded by `task.threads_max` (passed via queue prefix).
    try:
        child_jobs = [
            crawl_one_url.s(task_id, url, idx)
            for idx, url in enumerate(urls)
        ]
        # Use chunking to throttle concurrency
        chunk_size = max(task.threads_max, 1)
        groups = [group(child_jobs[i:i + chunk_size]) for i in range(0, len(child_jobs), chunk_size)]
        for g in groups:
            with allow_join_result():
                g.apply_async(queue="crawler")
                # Honor pause/stop between chunks
                task.refresh_from_db()
                if task.status in ("paused", "stopped"):
                    _log(task, f"task {task.status} detected, halting dispatch")
                    break
                # Random sleep between chunks
                time.sleep(random.uniform(task.interval_min, task.interval_max))
    except SoftTimeLimitExceeded:
        _log(task, "soft time limit exceeded")
        task.mark_error("soft time limit")
        _maybe_schedule_retry(task, "soft time limit exceeded")
    except Exception as e:
        _log(task, f"unexpected error: {e!r}")
        task.mark_error(repr(e))
        _maybe_schedule_retry(task, repr(e))
        return

    task.refresh_from_db()
    if task.status == "running":
        task.mark_done()
    _log(task, f"finished: success={task.success_items} failed={task.failed_items} skipped={task.skipped_items}")

    # Record scheduled run completion
    try:
        from .schedule import record_run
        record_run(task)
    except Exception as e:
        logger.warning(f"failed to record_run for task {task.id}: {e!r}")

    # v29: on success, reset retry counters + notify webhook
    try:
        from .retry import reset_retries
        reset_retries(task)
    except Exception:
        pass
    try:
        from apps.webhooks.engine import notify_task_done
        notify_task_done(task)
    except Exception:
        pass

    # v34: trigger downstream tasks based on dependency config
    try:
        _trigger_downstream_tasks(task, success=True)
    except Exception as e:
        logger.warning(f"failed to trigger downstream for task {task.id}: {e!r}")


def _trigger_downstream_tasks(parent_task, success: bool):
    """v34: Trigger downstream tasks whose `depends_on` is this task and condition matches."""
    from .models import CrawlerTask
    downstream_qs = CrawlerTask.objects.filter(
        depends_on=parent_task, trigger_on_dependency=True, enabled=True
    )
    for child in downstream_qs:
        # Check trigger condition
        cond = child.trigger_condition or "success"
        if cond == "success" and not success:
            _log(child, f"skip trigger from {parent_task.name}: parent failed but condition=success", level="info")
            continue
        if cond == "failure" and success:
            _log(child, f"skip trigger from {parent_task.name}: parent succeeded but condition=failure", level="info")
            continue
        _log(child, f"triggered by parent {parent_task.name} (success={success})")
        async_result = run_crawler_task.delay(child.id)
        child.celery_task_id = async_result.id
        child.status = "queued"
        child.save(update_fields=["celery_task_id", "status"])


def _maybe_schedule_retry(task, error: str):
    """v29: schedule a retry based on the error and the task's retry strategy."""
    try:
        from .retry import should_retry, record_retry
        should, delay, reason = should_retry(task, error)
        if not should:
            _log(task, f"retry skipped: {reason}", level="warning")
            try:
                from apps.webhooks.engine import notify_task_error
                notify_task_error(task, error)
            except Exception:
                pass
            # v34: trigger downstream tasks even on terminal failure
            try:
                _trigger_downstream_tasks(task, success=False)
            except Exception as e:
                logger.warning(f"failed to trigger downstream (failure path) for {task.id}: {e!r}")
            return
        record_retry(task, error)
        task.save()
        _log(task, f"retry scheduled: attempt {task.retry_count}/{task.retry_max} in {delay}s — {reason}")
        run_crawler_task.apply_async(args=[task.id], countdown=delay)
    except Exception as e:
        logger.warning(f"failed to schedule retry for task {task.id}: {e!r}")


@celery_app.task(bind=True, name="apps.crawler_tasks.tasks.crawl_one_url")
def crawl_one_url(self, task_id: int, url: str, idx: int):
    """Per-URL crawl — fetch + parse + store."""
    task = CrawlerTask.objects.filter(pk=task_id).first()
    if not task:
        return
    if task.status in ("paused", "stopped"):
        return

    _log(task, f"begin #{idx} {url}")
    try:
        from crawler_engine.pipeline import crawl_book_pipeline
        book, chapter_results = crawl_book_pipeline(task, url)

        # Progress accounting
        task.inc_progress(
            processed=1,
            success=1 if book else 0,
            skipped=0 if book else 1,
            failed=0 if book else 1,
        )
        _log(task, f"end #{idx} {url} → book={book.id if book else None} chapters={len(chapter_results)}")
    except SoftTimeLimitExceeded:
        task.inc_progress(processed=1, failed=1)
        _log(task, f"timeout #{idx} {url}")
    except Exception as e:
        task.inc_progress(processed=1, failed=1)
        _log(task, f"error #{idx} {url}: {e!r}", level="error")


def _build_urls(task: CrawlerTask) -> list[str]:
    """Resolve target_urls + url_range into a flat URL list."""
    urls: list[str] = list(task.target_urls or [])
    cfg = task.url_range or {}
    if cfg.get("enabled") and cfg.get("template"):
        start = cfg.get("start", 1)
        end = cfg.get("end", start)
        step = cfg.get("step", 1)
        urls.extend(
            cfg["template"].format(**{cfg.get("var", "page"): p})
            for p in range(start, end + 1, step)
        )
    return urls


def _log(task: CrawlerTask, msg: str, level: str = "info", url: str = "", payload: Any = None):
    CrawlerTaskLog.objects.create(
        task=task, level=level, message=msg, url=url,
        payload=payload or {},
    )
    logger.log(level.upper(), f"[task={task.id}] {msg}")
