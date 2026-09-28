"""Webhook dispatch engine — formats payloads per provider + sends."""

import hashlib
import hmac
import json
import time
import base64
import urllib.parse

import httpx
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from loguru import logger

from .models import WebhookDelivery, WebhookEndpoint


# Event type → default human-readable message template
EVENT_TEMPLATES = {
    "task.done":     "✅ 任务[{name}] 已完成（成功 {success} / 失败 {failed}）",
    "task.error":    "❌ 任务[{name}] 失败：{error}",
    "task.paused":   "⏸  任务[{name}] 已暂停",
    "task.stopped":  "🛑 任务[{name}] 已停止",
    "task.scheduled": "⏰ 任务[{name}] 已加入定时调度（下次 {next_run}）",
    "download.ready": "📥 文件已生成：{book_title}.{format} ({size} KB)",
    "system.error":  "⚠️ 系统错误：{message}",
}


def _format_message(event: str, context: dict) -> str:
    template = EVENT_TEMPLATES.get(event, f"📌 {event}: {context}")
    try:
        return template.format(**context)
    except (KeyError, ValueError):
        return f"📌 {event}: {json.dumps(context, ensure_ascii=False)}"


def _dingtalk_sign(secret: str, timestamp: int) -> str:
    if not secret:
        return ""  # v133: empty secret guard
    """Compute DingTalk robot signature (HMAC-SHA256, base64)."""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return urllib.parse.quote_plus(base64.b64encode(hmac_code))


def _build_dingtalk_payload(text: str, context: dict) -> dict:
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": "novel-system 通知",
            "text": f"### novel-system 通知\n\n{text}\n\n```\n{json.dumps(context, ensure_ascii=False, indent=2)}\n```",
        },
    }


def _build_wecom_payload(text: str, context: dict) -> dict:
    return {
        "msgtype": "markdown",
        "markdown": {"content": f"## novel-system 通知\n\n{text}"},
    }


def _build_slack_payload(text: str, context: dict) -> dict:
    return {
        "text": text,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        ],
    }


def _build_generic_payload(event: str, text: str, context: dict) -> dict:
    return {"event": event, "message": text, "context": context, "ts": time.time()}


def _send_email(to_addrs: list[str], subject: str, body: str) -> tuple[bool, str]:
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "novel-system@local"),
            recipient_list=to_addrs,
            fail_silently=False,
        )
        return True, ""
    except Exception as e:
        return False, repr(e)


def dispatch_event(event: str, context: dict) -> dict:
    """Dispatch an event to all subscribed webhook endpoints.

    Args:
        event: event type (e.g., "task.done")
        context: event payload (e.g., {name, success, failed, ...})

    Returns: {sent: int, failed: int, deliveries: [...]}
    """
    msg = _format_message(event, context)
    sent, failed, deliveries = 0, 0, []
    t0 = time.time()

    endpoints = WebhookEndpoint.objects.filter(enabled=True, events__contains=[event])
    for ep in endpoints:
        ok, status_code, response_text, err = False, None, "", ""
        try:
            if ep.provider == "dingtalk":
                ts = int(time.time() * 1000)
                url = ep.url
                if ep.secret:
                    sign = _dingtalk_sign(ep.secret, ts)
                    url = f"{url}&timestamp={ts}&sign={sign}"
                payload = _build_dingtalk_payload(msg, context)
                r = httpx.post(url, json=payload, timeout=10)
                ok = r.status_code == 200 and r.json().get("errcode") == 0
                status_code = r.status_code
                response_text = r.text
                if not ok:
                    err = response_text
            elif ep.provider == "wecom":
                payload = _build_wecom_payload(msg, context)
                r = httpx.post(ep.url, json=payload, timeout=10)
                ok = r.status_code == 200 and r.json().get("errcode") == 0
                status_code = r.status_code
                response_text = r.text
            elif ep.provider == "slack":
                payload = _build_slack_payload(msg, context)
                r = httpx.post(ep.url, json=payload, timeout=10)
                ok = r.status_code == 200
                status_code = r.status_code
                response_text = r.text
            elif ep.provider == "generic":
                payload = _build_generic_payload(event, msg, context)
                r = httpx.post(ep.url, json=payload, timeout=10)
                ok = r.status_code < 400
                status_code = r.status_code
                response_text = r.text
            elif ep.provider == "email":
                to_list = [x.strip() for x in (ep.email_to or "").split(",") if x.strip()]
                if not to_list:
                    ok = False
                    err = "no email_to configured"
                else:
                    ok, err = _send_email(to_list, f"[novel-system] {event}", msg)
                    status_code = 200 if ok else 500
        except Exception as e:
            err = repr(e)
            logger.warning(f"webhook dispatch failed: {ep.name} {event} {e!r}")

        # Update stats + create delivery record
        duration_ms = int((time.time() - t0) * 1000)
        delivery = WebhookDelivery.objects.create(
            endpoint=ep, event=event, payload={"message": msg, "context": context},
            status_code=status_code, response_text=response_text[:2000],
            success=ok, error=err, duration_ms=duration_ms,
        )
        deliveries.append({"endpoint": ep.name, "success": ok, "status": status_code})
        ep.sent_count = (ep.sent_count or 0) + 1
        ep.last_sent_at = timezone.now()
        if ok:
            sent += 1
        else:
            ep.fail_count = (ep.fail_count or 0) + 1
            ep.last_error = err
        ep.save(update_fields=["sent_count", "fail_count", "last_sent_at", "last_error"])

    return {"sent": sent, "failed": failed, "deliveries": deliveries}


# Convenience wrappers for common events
def notify_task_done(task) -> None:
    dispatch_event("task.done", {
        "name": task.name, "success": task.success_items,
        "failed": task.failed_items, "skipped": task.skipped_items,
    })


def notify_task_error(task, error: str) -> None:
    dispatch_event("task.error", {"name": task.name, "error": error})


def notify_download_ready(record) -> None:
    dispatch_event("download.ready", {
        "book_title": record.book.title,
        "format": record.output_format,
        "size": int(record.file_size / 1024),
    })
