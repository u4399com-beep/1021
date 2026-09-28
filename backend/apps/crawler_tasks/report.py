"""Task execution report generator (v48) — produce a PDF summary."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from django.conf import settings
from loguru import logger


def generate_task_report(task, format: str = "txt") -> Path:
    """Generate a report file for a completed task.

    format: 'txt' (default) or 'json'. PDF requires reportlab (lazy import).
    """
    report_dir = Path(settings.MEDIA_ROOT) / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"task_{task.id}_{ts}.{format}"
    out_path = report_dir / filename

    data = {
        "task_id": task.id, "task_name": task.name,
        "status": task.status, "mode": task.mode,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "total_items": task.total_items, "processed": task.processed_items,
        "success": task.success_items, "failed": task.failed_items, "skipped": task.skipped_items,
        "priority": task.priority, "retry_count": task.retry_count,
        "last_error": task.last_error[:500] if task.last_error else None,
        "logs": [{"level": l.level, "message": l.message, "ts": l.created_at.isoformat()}
                 for l in task.logs.all()[:50]],
    }

    if format == "json":
        import json
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    elif format == "pdf":
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            # Register a CJK font
            font_path = "/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf"
            try:
                pdfmetrics.registerFont(TTFont("NotoSansSC", font_path))
                base_font = "NotoSansSC"
            except Exception:
                base_font = "Helvetica"
            doc = SimpleDocTemplate(str(out_path), pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            title_style = styles["Title"]
            title_style.fontName = base_font
            story.append(Paragraph(f"采集任务报告 — {task.name}", title_style))
            story.append(Spacer(1, 20))
            for k, v in data.items():
                if k == "logs": continue
                story.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))
                story.append(Spacer(1, 6))
            story.append(Spacer(1, 20))
            story.append(Paragraph("<b>日志（最近 50 条）</b>", styles["Heading2"]))
            for log in data["logs"]:
                story.append(Paragraph(f"[{log['level']}] {log['message'][:100]}", styles["Normal"]))
            doc.build(story)
        except ImportError:
            # Fallback to txt if reportlab not available
            format = "txt"
            out_path = out_path.with_suffix(".txt")

    if format == "txt":
        lines = [f"采集任务报告 — {task.name}", "=" * 50, ""]
        for k, v in data.items():
            if k == "logs": continue
            lines.append(f"{k}: {v}")
        lines.append("")
        lines.append("日志（最近 50 条）:")
        lines.append("-" * 30)
        for log in data["logs"]:
            lines.append(f"[{log['level']}] {log['message'][:200]}")
        out_path.write_text("\n".join(lines), encoding="utf-8")

    return out_path
