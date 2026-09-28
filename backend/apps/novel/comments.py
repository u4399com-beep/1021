"""Chapter comment system (v91)."""
from __future__ import annotations
from django.db import models

class ChapterComment(models.Model):
    reader = models.ForeignKey("account.ReaderProfile", on_delete=models.CASCADE, related_name="comments")
    chapter = models.ForeignKey("novel.Chapter", on_delete=models.CASCADE, related_name="comments")
    content = models.TextField("评论内容", max_length=500)
    is_spoiler = models.BooleanField("剧透标记", default=False)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    likes = models.IntegerField("点赞", default=0)
    is_deleted = models.BooleanField("已删除", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "novel_chapter_comment"
        verbose_name = "章节评论"
        verbose_name_plural = verbose_name
        ordering = ("-id",)
