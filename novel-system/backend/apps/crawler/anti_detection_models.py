"""DB-backed UA/Cookie pools (v134) — replace hardcoded lists with DB models."""
from django.db import models


class UserAgentPool(models.Model):
    """Rotating User-Agent strings stored in DB for easy management."""
    user_agent = models.TextField("UA 字符串", unique=True)
    browser = models.CharField("浏览器", max_length=32, default="chrome",
        choices=[("chrome", "Chrome"), ("firefox", "Firefox"), ("safari", "Safari"),
                 ("edge", "Edge"), ("mobile", "移动端")])
    os = models.CharField("操作系统", max_length=32, default="windows",
        choices=[("windows", "Windows"), ("mac", "macOS"), ("linux", "Linux"),
                 ("android", "Android"), ("ios", "iOS")])
    is_active = models.BooleanField("启用", default=True)
    use_count = models.IntegerField("使用次数", default=0)
    last_used_at = models.DateTimeField("最后使用", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crawler_ua_pool"
        verbose_name = "UA 池"
        verbose_name_plural = verbose_name
        ordering = ("-use_count",)

    def __str__(self):
        return self.user_agent[:60] + "..."


class CookiePool(models.Model):
    """Rotating cookies for sites that require session-based access."""
    site_domain = models.CharField("站点域名", max_length=255, db_index=True)
    cookies = models.JSONField("Cookie 键值对", default=dict,
        help_text='{"sessionid": "xxx", "csrf": "yyy"}')
    is_active = models.BooleanField("启用", default=True)
    use_count = models.IntegerField("使用次数", default=0)
    last_used_at = models.DateTimeField("最后使用", null=True, blank=True)
    expires_at = models.DateTimeField("过期时间", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crawler_cookie_pool"
        verbose_name = "Cookie 池"
        verbose_name_plural = verbose_name
        ordering = ("site_domain",)

    def __str__(self):
        return f"{self.site_domain} ({len(self.cookies)} cookies)"


class FingerprintProfile(models.Model):
    """Browser fingerprint profiles for Playwright randomization."""
    name = models.CharField("名称", max_length=64, unique=True)
    viewport_width = models.IntegerField("视口宽", default=1366)
    viewport_height = models.IntegerField("视口高", default=768)
    locale = models.CharField("区域", max_length=16, default="zh-CN")
    timezone = models.CharField("时区", max_length=64, default="Asia/Shanghai")
    platform = models.CharField("平台", max_length=64, default="Win32")
    hardware_concurrency = models.IntegerField("CPU 核数", default=4)
    device_memory = models.IntegerField("内存(GB)", default=8)
    is_active = models.BooleanField("启用", default=True)
    use_count = models.IntegerField("使用次数", default=0)

    class Meta:
        db_table = "crawler_fingerprint"
        verbose_name = "浏览器指纹"
        verbose_name_plural = verbose_name
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.viewport_width}x{self.viewport_height})"
