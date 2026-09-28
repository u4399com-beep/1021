"""Distributed task scheduling (v74) — multi-node worker cluster support."""
from django.core.cache import cache


_WORKER_REGISTRY_KEY = "crawler:workers:registry"


def register_worker(hostname: str, queues: list[str], max_concurrency: int = 4) -> dict:
    """Register a worker node in the cluster."""
    import time
    workers = cache.get(_WORKER_REGISTRY_KEY, {})
    workers[hostname] = {
        "hostname": hostname, "queues": queues,
        "max_concurrency": max_concurrency,
        "registered_at": time.time(),
        "last_heartbeat": time.time(),
    }
    cache.set(_WORKER_REGISTRY_KEY, workers, timeout=3600)
    return workers[hostname]


def heartbeat(hostname: str) -> None:
    """Update worker heartbeat."""
    import time
    workers = cache.get(_WORKER_REGISTRY_KEY, {})
    if hostname in workers:
        workers[hostname]["last_heartbeat"] = time.time()
        cache.set(_WORKER_REGISTRY_KEY, workers, timeout=3600)


def get_active_workers() -> list[dict]:
    """Return all active workers (heartbeat within 60s)."""
    import time
    workers = cache.get(_WORKER_REGISTRY_KEY, {})
    now = time.time()
    active = [w for w in workers.values() if now - w.get("last_heartbeat", 0) < 60]
    return active


def cluster_stats() -> dict:
    """Return cluster statistics."""
    workers = get_active_workers()
    total_concurrency = sum(w.get("max_concurrency", 0) for w in workers)
    return {
        "active_workers": len(workers),
        "total_concurrency": total_concurrency,
        "workers": [{"hostname": w["hostname"], "queues": w["queues"],
                      "max_concurrency": w["max_concurrency"]} for w in workers],
    }
