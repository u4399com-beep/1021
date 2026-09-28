"""Audit log models — record user actions for compliance / debugging."""
from __future__ import annotations

from django.db import models


class AuditEntry(models.Model):
    """A single user action (login, rule edit, task run, etc.).

    Stored in a separate table (not in user's session) for long-term retention.
    """

    ACTION_CHOICES = (
        ("login", "登录"),
        ("logout", "退出"),
        ("view", "查看"),
        ("create", "创建"),
        ("update", "更新"),
        ("delete", "删除"),
        ("run", "执行"),
        ("pause", "暂停"),
        ("stop", "停止"),
        ("export", "导出"),
        ("upload", "上传"),
        ("download", "下载"),
    )

    user_id = models.IntegerField("用户ID", null=True, blank=True, db_index=True)
    username = models.CharField("用户名", max_length=64, blank=True, db_index=True)
    action = models.CharField("动作", max_length=16, choices=ACTION_CHOICES, db_index=True)
    resource = models.CharField("资源类型", max_length=64, blank=True, help_text="如 'book'/'rule'/'task'")
    resource_id = models.CharField("资源ID", max_length=64, blank=True)
    method = models.CharField("HTTP 方法", max_length=8, blank=True)
    path = models.CharField("路径", max_length=255, blank=True, db_index=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("UA", max_length=255, blank=True)
    payload = models.JSONField("载荷", default=dict, blank=True,
        help_text="请求体的关键信息（不含密码/敏感字段）")
    status_code = models.IntegerField("HTTP 状态码", null=True, blank=True)
    success = models.BooleanField("成功", default=True)
    error = models.TextField("错误信息", blank=True)
    duration_ms = models.IntegerField("耗时(ms)", default=0)
    created_at = models.DateTimeField("时间", auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_log"
        verbose_name = "审计日志"
        verbose_name_plural = verbose_name
        ordering = ("-id",)
        indexes = [
            models.Index(fields=["user_id", "action", "created_at"]),
            models.Index(fields=["resource", "resource_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.username} {self.action} {self.resource}/{self.resource_id}"
