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
    # Auto-disable thresholds
    auto_disable_enabled = models.BooleanField("启用自动剔除", default=True)
    min_success_rate = models.FloatField("最低成功率阈值", default=0.30,
        help_text="当成功率低于此值时自动剔除（0.0~1.0）")
    min_sample_count = models.IntegerField("最少统计样本数", default=5,
        help_text="成功+失败次数累计达到此值后才参与剔除判断")
    auto_disabled_at = models.DateTimeField("自动剔除时间", null=True, blank=True)
    auto_disabled_reason = models.CharField("剔除原因", max_length=255, blank=True)
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

    @property
    def total_requests(self) -> int:
        return self.success_count + self.failure_count

    @property
    def should_auto_disable(self) -> bool:
        """Whether this proxy should be auto-disabled based on success rate."""
        if not self.auto_disable_enabled:
            return False
        if self.total_requests < self.min_sample_count:
            return False
        return self.success_rate < self.min_success_rate

    def record_success(self):
        """Record a successful request, return True if proxy was auto-disabled."""
        from django.utils import timezone
        self.success_count += 1
        self.last_used_at = timezone.now()
        if self.should_auto_disable:
            self.is_active = False
            self.auto_disabled_at = timezone.now()
            self.auto_disabled_reason = (
                f"自动剔除：成功率 {self.success_rate:.1%} 低于阈值 {self.min_success_rate:.1%}"
            )
            self.save(update_fields=["success_count", "last_used_at", "is_active",
                                     "auto_disabled_at", "auto_disabled_reason"])
            return True
        self.save(update_fields=["success_count", "last_used_at"])
        return False

    def record_failure(self):
        """Record a failed request, return True if proxy was auto-disabled."""
        from django.utils import timezone
        self.failure_count += 1
        self.last_used_at = timezone.now()
        if self.should_auto_disable:
            self.is_active = False
            self.auto_disabled_at = timezone.now()
            self.auto_disabled_reason = (
                f"自动剔除：成功率 {self.success_rate:.1%} 低于阈值 {self.min_success_rate:.1%}"
            )
            self.save(update_fields=["failure_count", "last_used_at", "is_active",
                                     "auto_disabled_at", "auto_disabled_reason"])
            return True
        self.save(update_fields=["failure_count", "last_used_at"])
        return False

    def reactivate(self):
        """Manually reactivate an auto-disabled proxy."""
        from django.utils import timezone
        self.is_active = True
        self.auto_disabled_at = None
        self.auto_disabled_reason = ""
        self.success_count = 0
        self.failure_count = 0
        self.save(update_fields=["is_active", "auto_disabled_at",
                                 "auto_disabled_reason", "success_count", "failure_count"])
