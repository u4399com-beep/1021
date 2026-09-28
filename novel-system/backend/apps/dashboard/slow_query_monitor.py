"""Slow query monitor (v52) — track queries slower than threshold."""
import time
from django.core.cache import cache


SLOW_QUERY_THRESHOLD_MS = 500  # 500ms
_SLOW_QUERIES_KEY = "dashboard:slow_queries"
_MAX_STORED = 100


class SlowQueryLogger:
    """Middleware-style logger that records slow queries."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time.time()
        response = self.get_response(request)
        duration_ms = (time.time() - t0) * 1000
        if duration_ms > SLOW_QUERY_THRESHOLD_MS:
            entry = {
                "path": request.path, "method": request.method,
                "duration_ms": round(duration_ms, 1),
                "ts": time.time(),
            }
            queries = cache.get(_SLOW_QUERIES_KEY, [])
            queries.insert(0, entry)
            cache.set(_SLOW_QUERIES_KEY, queries[:_MAX_STORED], timeout=86400)
        return response


def get_slow_queries(limit: int = 50) -> list:
    return cache.get(_SLOW_QUERIES_KEY, [])[:limit]


def clear_slow_queries():
    cache.delete(_SLOW_QUERIES_KEY)
