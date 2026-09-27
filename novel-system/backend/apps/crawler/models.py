"""ProxyPool model — user-maintained HTTP/HTTPS proxy list.

A pool of static proxies (IP:port) that the fetcher can round-robin through.
Hyperbrowser sessions are managed separately in cache (see anti_detection/pool.py).
"""
from __future__ import annotations

from django.db import models


class ProxyPool(models.Model):
    """A single proxy entry."""

    PROXY_TYPES = (
        ("http", "HTTP"),
        ("https", "HTTPS"),
        ("socks5", "SOCKS5"),
    )

    name = models.CharField("名称", max_length=64, blank=True, help_text="便于识别，例：北京-1")
    url = models.CharField("代理URL", max_length=255, help_text="例：http://user:pass@ip:port 或 socks5://ip:port")
    proxy_type = models.CharField("类型", max_length=8, choices=PROXY_TYPES, default="http")
    region = models.CharField("地区", max_length=64, blank=True, help_text="例：北京 / 上海")
    is_active = models.BooleanField("启用", default=True)
    priority = models.IntegerField("优先级", default=100)
    success_count = models.IntegerField("成功次数", default=0)
    failure_count = models.IntegerField("失败次数", default=0)
    last_used_at = models.DateTimeField("最近使用", null=True, blank=True)
    last_check_at = models.DateTimeField("最近检测", null=True, blank=True)
    last_check_ok = models.BooleanField("最近检测", null=True, blank=True)
    notes = models.TextField("备注", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crawler_proxy_pool"
        verbose_name = "代理池"
        verbose_name_plural = verbose_name
        ordering = ("-priority", "id")

    def __str__(self) -> str:
        return f"{self.name or self.url} ({self.proxy_type}, prio={self.priority})"

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return (self.success_count / total) if total else 0.0
