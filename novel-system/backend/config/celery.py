"""Celery app factory."""
from __future__ import annotations

import os

from celery import Celery
from celery.signals import worker_ready
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("novel_system")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@worker_ready.connect
def on_worker_ready(sender, **_):
    """Emit a heartbeat when worker starts."""
    print(f"[celery] worker ready: {sender.hostname}", flush=True)


@app.task(bind=True)
def debug_task(self):  # pragma: no cover
    print(f"Request: {self.request!r}")
