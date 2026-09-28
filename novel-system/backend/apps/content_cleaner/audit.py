"""Chapter content audit (v46) — detect banned/sensitive keywords."""
import re
from django.db import models


class BannedKeyword(models.Model):
    """敏感词库"""
    word = models.CharField("敏感词", max_length=128, unique=True)
    category = models.CharField("分类", max_length=32, default="general",
        choices=[("general", "通用"), ("political", "政治"), ("adult", "成人"), ("violence", "暴力")])
    severity = models.CharField("严重度", max_length=16, default="warning",
        choices=[("info", "提示"), ("warning", "警告"), ("critical", "严重")])
    replacement = models.CharField("替换为", max_length=128, blank=True, default="***")
    enabled = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cleaner_banned_keyword"
        verbose_name = "敏感词"
        verbose_name_plural = verbose_name


def audit_text(text: str) -> dict:
    """Scan text for banned keywords. Returns {hits, clean_text}."""
    if not text:
        return {"hits": [], "clean_text": text}
    hits = []
    clean = text
    for kw in BannedKeyword.objects.filter(enabled=True):
        if kw.word in clean:
            hits.append({
                "word": kw.word, "category": kw.category,
                "severity": kw.severity, "count": clean.count(kw.word),
            })
            if kw.replacement:
                clean = clean.replace(kw.word, kw.replacement)
    return {"hits": hits, "hit_count": len(hits), "clean_text": clean,
            "is_clean": len(hits) == 0}


def audit_chapter(chapter) -> dict:
    """Audit a chapter's content. Auto-clean if critical hits found."""
    result = audit_text(chapter.content or "")
    critical_hits = [h for h in result["hits"] if h["severity"] == "critical"]
    if critical_hits and result["clean_text"] != chapter.content:
        chapter.content = result["clean_text"]
        chapter.save(update_fields=["content"])
    return {**result, "chapter_id": chapter.id, "auto_cleaned": bool(critical_hits)}
