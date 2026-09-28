"""Error-aware retry decision (v29).

Decides whether a failed task should be retried based on error type:
  - HTTP 5xx / timeout / network → retry (transient)
  - HTTP 429 (rate limit) → retry with longer delay
  - HTTP 403 / WAF captcha → retry (captcha auto-solve may work on second pass)
  - HTTP 404 / content missing → DON'T retry (permanent)
  - HTML parse error → DON'T retry (rule issue, not transient)
  - Chapter content empty → DON'T retry (parser issue)
"""

import re
import time

from django.utils import timezone


# Error category → (should_retry, extra_delay_seconds)
RETRY_DECISIONS = {
    "transient_network":    (True,  0),    # timeout / connection error
    "transient_http_5xx":   (True,  10),   # 502 / 503 / 504
    "transient_http_429":   (True,  60),   # rate-limited — wait longer
    "waf_captcha":          (True,  30),   # captcha detected, may solve next time
    "permanent_http_404":    (False, 0),
    "permanent_http_403":    (False, 0),    # banned — retry unlikely to help
    "parser_missing":       (False, 0),    # rule doesn't match — won't fix by retry
    "content_empty":        (False, 0),    # parser returned empty — config issue
    "unknown":              (True,  30),  # default: retry once conservatively
}


def classify_error(error: str) -> str:
    """Classify an error message into a category."""
    err = (error or "").lower()
    if "captcha" in err or "waf" in err or "goedge" in err:
        return "waf_captcha"
    if "429" in err or "rate limit" in err or "too many" in err:
        return "transient_http_429"
    if "403" in err or "forbidden" in err:
        return "permanent_http_403"
    if "404" in err or "not found" in err:
        return "permanent_http_404"
    if "timeout" in err or "timed out" in err:
        return "transient_network"
    if "connection" in err and ("refused" in err or "reset" in err or "closed" in err):
        return "transient_network"
    if "5xx" in err or "500" in err or "502" in err or "503" in err or "504" in err:
        return "transient_http_5xx"
    if "parse" in err or "selector" in err or "no html" in err:
        return "parser_missing"
    if "empty" in err and ("content" in err or "html" in err):
        return "content_empty"
    return "unknown"


def should_retry(task, error: str) -> tuple[bool, int, str]:
    """Decide if a task should be retried after failure.

    Returns (should_retry, delay_seconds, reason).
    """
    if task.retry_strategy == "never":
        return False, 0, "retry_strategy=never"
    if task.retry_count >= task.retry_max:
        return False, 0, f"max retries ({task.retry_max}) reached"

    if task.retry_strategy == "always":
        delay = int(task.retry_delay * (task.retry_backoff ** task.retry_count))
        return True, delay, "retry_strategy=always"

    # error_aware
    category = classify_error(error)
    should, extra_delay = RETRY_DECISIONS.get(category, (True, 30))
    if not should:
        return False, 0, f"error category '{category}' is permanent"

    base_delay = task.retry_delay or 30
    backoff = task.retry_backoff or 2.0
    delay = int(base_delay * (backoff ** task.retry_count) + extra_delay)
    return True, delay, f"error category '{category}' — retry after {delay}s"


def record_retry(task, error: str) -> dict:
    """Append a retry attempt to task.retry_history and increment retry_count.

    Returns the new retry_history entry.
    """
    entry = {
        "attempt": task.retry_count + 1,
        "error": error[:500],
        "ts": timezone.now().isoformat(),
    }
    history = list(task.retry_history or [])
    history.append(entry)
    task.retry_history = history[-20:]  # cap at 20 entries
    task.retry_count += 1
    return entry


def reset_retries(task):
    """Clear retry counters — call after a successful run."""
    task.retry_count = 0
    task.retry_history = []
    task.save(update_fields=["retry_count", "retry_history"])
