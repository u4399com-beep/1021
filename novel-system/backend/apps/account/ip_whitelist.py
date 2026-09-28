"""IP whitelist (v51) — restrict admin/API access to whitelisted IPs."""
from django.core.cache import cache
from django.db import models


class IPWhitelist(models.Model):
    """Whitelisted IP for admin/API access."""
    ip = models.GenericIPAddressField("IP", unique=True)
    label = models.CharField("标签", max_length=64, blank=True, help_text="如：办公室")
    enabled = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "account_ip_whitelist"
        verbose_name = "IP 白名单"
        verbose_name_plural = verbose_name

    def __str__(self): return f"{self.ip} ({self.label})"


def is_ip_whitelisted(ip: str) -> bool:
    """Check if an IP is in the whitelist (cached)."""
    if not ip:
        return False
    cached = cache.get("ip_whitelist", None)
    if cached is None:
        cached = set(IPWhitelist.objects.filter(enabled=True).values_list("ip", flat=True))
        cache.set("ip_whitelist", cached, timeout=300)
    return ip in cached
