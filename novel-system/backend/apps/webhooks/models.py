"""Webhook models — supports DingTalk / WeCom / Slack / generic HTTP."""

from django.db import models


class WebhookEndpoint(models.Model):
    """A webhook destination (DingTalk, WeCom Work, Slack, custom HTTP)."""

    PROVIDER_CHOICES = (
        ("dingtalk", "钉钉"),
        ("wecom", "企业微信"),
        ("slack", "Slack"),
        ("generic", "通用 HTTP POST"),
        ("email", "邮件 (SMTP)"),
    )

    name = models.CharField("名称", max_length=64, unique=True)
    provider = models.CharField("类型", max_length=16, choices=PROVIDER_CHOICES, default="dingtalk")
    url = models.URLField("URL", max_length=500, blank=True, help_text="钉钉/企业微信机器人 webhook URL")
    secret = models.CharField("加签密钥", max_length=128, blank=True, help_text="钉钉机器人加签密钥（可选）")
    email_to = models.TextField("收件人", blank=True, help_text="邮件用，逗号分隔")

    enabled = models.BooleanField("启用", default=True)
    # Event types this endpoint subscribes to (JSON list)
    events = models.JSONField("订阅事件", default=list, help_text='例 ["task.done","task.error","download.ready"]')

    notes = models.TextField("备注", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Stats
    sent_count = models.IntegerField("发送次数", default=0)
    fail_count = models.IntegerField("失败次数", default=0)
    last_sent_at = models.DateTimeField("最近发送", null=True, blank=True)
    last_error = models.TextField("最近错误", blank=True)

    class Meta:
        db_table = "webhook_endpoint"
        verbose_name = "Webhook 端点"
        verbose_name_plural = verbose_name
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.provider})"


class WebhookDelivery(models.Model):
    """Single delivery record — useful for debugging / audit."""

    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries")
    event = models.CharField("事件类型", max_length=64, db_index=True)
    payload = models.JSONField("载荷")
    status_code = models.IntegerField("HTTP 状态码", null=True, blank=True)
    response_text = models.TextField("响应内容", blank=True)
    success = models.BooleanField("成功", default=False)
    error = models.TextField("错误信息", blank=True)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    duration_ms = models.IntegerField("耗时(ms)", default=0)

    class Meta:
        db_table = "webhook_delivery"
        verbose_name = "Webhook 投递记录"
        verbose_name_plural = verbose_name
        ordering = ("-sent_at",)
        indexes = [
            models.Index(fields=["endpoint", "event", "sent_at"]),
        ]
