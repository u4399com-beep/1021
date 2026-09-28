"""Site traffic stats (v63) — PV/UV by page type."""
from datetime import timedelta
from django.db import models
from django.utils import timezone


class PageView(models.Model):
    """Single page view record."""
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="page_views", null=True, blank=True)
    host = models.CharField("域名", max_length=255, db_index=True)
    page_type = models.CharField("页面类型", max_length=32,
        choices=[("home", "首页"), ("book", "书籍页"), ("chapter", "章节页"), ("category", "分类页"), ("search", "搜索页")])
    path = models.CharField("路径", max_length=255)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("UA", max_length=255, blank=True)
    referer = models.CharField("来源", max_length=255, blank=True)
    response_ms = models.IntegerField("响应时间(ms)", default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "sites_page_view"
        verbose_name = "页面浏览"
        verbose_name_plural = verbose_name
        ordering = ("-id",)
        indexes = [
            models.Index(fields=["host", "page_type", "-created_at"]),
        ]


def record_page_view(host: str, path: str, page_type: str = "home",
                     ip: str = "", user_agent: str = "", referer: str = "",
                     response_ms: int = 0, site_id: int | None = None):
    """Record a page view (async-friendly — minimal fields)."""
    return PageView.objects.create(
        site_id=site_id, host=host, page_type=page_type, path=path[:255],
        ip=ip or None, user_agent=user_agent[:255], referer=referer[:255],
        response_ms=response_ms,
    )


def traffic_summary(host: str, days: int = 7) -> dict:
    """Return PV/UV summary for a host."""
    since = timezone.now() - timedelta(days=days)
    qs = PageView.objects.filter(host=host, created_at__gte=since)
    total_pv = qs.count()
    unique_ips = qs.values("ip").distinct().count()
    by_type = {}
    for pt, label in PageView._meta.get_field("page_type").choices:
        count = qs.filter(page_type=pt).count()
        if count:
            by_type[pt] = {"label": label, "pv": count}
    return {
        "host": host, "days": days,
        "total_pv": total_pv, "unique_visitors": unique_ips,
        "by_page_type": by_type,
    }
