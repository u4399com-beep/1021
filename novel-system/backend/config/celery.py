"""Celery app factory — v99: acks_late + max_retries to prevent stuck tasks."""
from __future__ import annotations

import os

from celery import Celery
from celery.signals import worker_ready

load_dotenv = None
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("novel_system")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autoretry_for = (Exception,)
app.conf.update(
    task_acks_late=True,              # v99: ack only after task completes
    task_reject_on_worker_lost=True,   # v99: requeue if worker crashes
    task_max_retries=3,                # v99: cap retries to prevent infinite loops
    worker_prefetch_multiplier=1,      # v99: fair dispatching
)

app.autodiscover_tasks()


@worker_ready.connect
def on_worker_ready(sender, **_):
    print(f"[celery] worker ready: {sender.hostname}", flush=True)


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
