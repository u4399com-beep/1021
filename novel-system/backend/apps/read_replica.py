"""Database router for read/write splitting (v25).

Goal: route read-only queries (e.g., front-end page rendering) to the
read replica, while writes always go to the primary.

Strategy:
  - All apps default to 'default' (primary)
  - When `DATABASE_REPLICA_ENABLED` setting is True, queries from
    specific read-heavy patterns can be routed to the 'replica' DB
  - We use a simple heuristic: GET requests and SELECTs from
    front-end views use 'replica'; everything else uses 'default'

Configuration in settings:
  DATABASES = {
      'default': {...primary...},
      'replica': {...replica...},
  }
  DATABASE_REPLICA_ENABLED = True  # set in .env

Manual override (in code):
  from apps.read_replica import use_replica
  with use_replica():
      qs = Book.objects.all()  # routed to replica
"""

import threading
from contextlib import contextmanager
from typing import Iterator

from django.conf import settings


# Thread-local flag to force replica for the current scope
_force_replica = threading.local()


def is_replica_enabled() -> bool:
    return getattr(settings, "DATABASE_REPLICA_ENABLED", False) and "replica" in settings.DATABASES


@contextmanager
def use_replica() -> Iterator[None]:
    """Force the current scope to use the read replica DB.

    Usage:
        from apps.read_replica import use_replica
        with use_replica():
            books = Book.objects.filter(...)
    """
    prev = getattr(_force_replica, "value", False)
    _force_replica.value = True
    try:
        yield
    finally:
        _force_replica.value = prev


class ReadReplicaRouter:
    """Django DB router that routes reads to replica when enabled."""

    def _is_forced(self) -> bool:
        return getattr(_force_replica, "value", False)

    def db_for_read(self, model, **hints):
        if is_replica_enabled() and self._is_forced():
            return "replica"
        return "default"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations between any DBs in the same project
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Only migrate on primary — replica is read-only
        return db == "default"
