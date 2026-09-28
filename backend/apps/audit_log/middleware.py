"""Audit log middleware — records every API request to the audit_log table.

Skips:
  - GET requests to /admin/ (Django admin already logs)
  - Static / media requests
  - OPTIONS preflight requests

Records:
  - User (resolved from JWT)
  - HTTP method + path
  - Action inferred from method + path
  - Resource + resource_id extracted from path
  - Status code + duration
"""
from __future__ import annotations

import re
import time
import json
from typing import Any

from django.http import HttpRequest, HttpResponse


_SKIP_PREFIXES = ("/static/", "/media/", "/.well-known/")


# Method → default action
_METHOD_ACTION = {
    "GET": "view",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


# Path pattern → (resource, action_override)
# Examples:
#   /api/v1/auth/login/        → (auth, login)
#   /api/v1/tasks/5/run/       → (task, run)
#   /api/v1/novels/books/12/   → (book, view/update)
_PATH_PATTERNS = [
    (re.compile(r"/api/v1/auth/login/?$"), "auth", "login"),
    (re.compile(r"/api/v1/auth/logout/?$"), "auth", "logout"),
    (re.compile(r"/api/v1/tasks/(\d+)/run/?$"), "task", "run"),
    (re.compile(r"/api/v1/tasks/(\d+)/pause/?$"), "task", "pause"),
    (re.compile(r"/api/v1/tasks/(\d+)/stop/?$"), "task", "stop"),
    (re.compile(r"/api/v1/tasks/(\d+)/preempt/?$"), "task", "run"),
    (re.compile(r"/api/v1/tasks/batch_run/?$"), "task", "run"),
    (re.compile(r"/api/v1/crawler/engine/test/?$"), "crawler_engine", "run"),
    (re.compile(r"/api/v1/crawler/engine/fetch/?$"), "crawler_engine", "run"),
    (re.compile(r"/api/v1/downloads/generate/generate/?$"), "download", "create"),
    (re.compile(r"/api/v1/downloads/generate/generate-drm/?$"), "download_drm", "create"),
    (re.compile(r"/api/v1/themes/upload/?$"), "theme", "upload"),
    (re.compile(r"/api/v1/export/books/?$"), "book", "export"),
    (re.compile(r"/api/v1/export/tasks/?$"), "task", "export"),
    (re.compile(r"/api/v1/obfuscator/profiles/?$"), "obfuscation_profile", "create"),
    (re.compile(r"/api/v1/obfuscator/profiles/(\d+)/?$"), "obfuscation_profile", "update"),
    (re.compile(r"/api/v1/sites/?$"), "site", "create"),
    (re.compile(r"/api/v1/sites/(\d+)/?$"), "site", "update"),
    (re.compile(r"/api/v1/novels/books/?$"), "book", "create"),
    (re.compile(r"/api/v1/novels/books/(\d+)/?$"), "book", "update"),
    (re.compile(r"/api/v1/rules/?$"), "rule", "create"),
    (re.compile(r"/api/v1/rules/(\d+)/?$"), "rule", "update"),
]


def _classify_request(method: str, path: str) -> tuple[str, str, str]:
    """Return (resource, resource_id, action)."""
    for pat, resource, action in _PATH_PATTERNS:
        m = pat.match(path)
        if m:
            resource_id = m.group(1) if m.groups() else ""
            # If action is None, infer from method
            final_action = action or _METHOD_ACTION.get(method, "view")
            return resource, resource_id, final_action

    # Generic fallback: derive resource from path
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 4:
        resource = parts[3]  # /api/v1/<resource>/
    else:
        resource = "unknown"
    action = _METHOD_ACTION.get(method, "view")
    return resource, "", action


def _sanitize_payload(payload: Any) -> dict:
    """Strip sensitive fields from request payload before logging."""
    if not isinstance(payload, dict):
        try:
            # Try to parse JSON body
            if isinstance(payload, (bytes, str)):
                return {"_raw": str(payload)[:200]}
            return {"_value": str(payload)[:200]}
        except Exception:
            return {}
    # Strip keys that look sensitive
    sensitive_keys = {"password", "old_password", "new_password", "secret",
                      "api_key", "apikey", "token", "access_token", "refresh_token",
                      "FIRECRAWL_API_KEY", "OPENAI_API_KEY", "HYPERBROWSER_API_KEY",
                      "BROWSER_USE_OPENAI_API_KEY"}
    return {k: "***" if k in sensitive_keys else v for k, v in payload.items()}


class AuditLogMiddleware:
    """Record API requests to audit_log table."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip non-API requests
        path = request.path
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return self.get_response(request)

        t0 = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - t0) * 1000)

        # Skip successful GET to admin pages — already logged by Django
        if path.startswith("/admin/") and request.method == "GET":
            return response

        # Skip OPTIONS preflight
        if request.method == "OPTIONS":
            return response

        # Resolve user (best-effort)
        user_id = None
        username = ""
        try:
            if hasattr(request, "user") and request.user.is_authenticated:
                user_id = request.user.id
                username = request.user.username
        except Exception:
            pass

        # Classify
        resource, resource_id, action = _classify_request(request.method, path)

        # Extract payload (sanitized)
        payload = {}
        try:
            if request.method in ("POST", "PUT", "PATCH"):
                if request.content_type and "json" in request.content_type:
                    try:
                        raw = json.loads(request.body.decode("utf-8"))
                        payload = _sanitize_payload(raw)
                    except Exception:
                        pass
                elif request.content_type and "multipart" in request.content_type:
                    payload = {"_form": "multipart upload"}
        except Exception:
            pass

        # Get client IP
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        # Write to DB (best-effort — never block the response)
        try:
            from .models import AuditEntry
            AuditEntry.objects.create(
                user_id=user_id,
                username=username,
                action=action,
                resource=resource,
                resource_id=resource_id,
                method=request.method,
                path=path[:255],
                ip=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
                payload=payload,
                status_code=response.status_code,
                success=response.status_code < 400,
                error="" if response.status_code < 400 else f"HTTP {response.status_code}",
                duration_ms=duration_ms,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"audit log write failed: {e!r}")

        return response
