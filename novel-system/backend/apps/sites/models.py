"""站群管理模型。

设计要点：
- 多个 Site 共享同一套数据库与后台
- 每个 Site 拥有独立域名、主题模板、TDK、SEO/GEO 配置
- 偏移量 `offset` 用于书籍顺序错位展示（站间去重 SEO）
- 每个 Site 启用时自动生成对应的 nginx 配置文件
"""

from django.core.cache import cache
from django.db import models


class Theme(models.Model):
    """5 套前台主题模板注册表"""

    CODE_CHOICES = (
        ("simple_reading", "简约阅读"),
        ("classic_shelf", "古典书架"),
        ("magazine_modern", "杂志现代"),
        ("dark_tech", "暗黑科技"),
        ("minimal_rank", "极简榜单"),
    )

    code = models.CharField("代码", max_length=32, unique=True, choices=CODE_CHOICES)
    name = models.CharField("主题名", max_length=64)
    description = models.TextField("描述", blank=True)
    preview = models.URLField("预览图URL", blank=True)
    is_active = models.BooleanField("启用", default=True)

    # Theme-specific options — extended by each theme package
    config_schema = models.JSONField("配置 schema", default=dict, blank=True)
    default_config = models.JSONField("默认配置", default=dict, blank=True)

    class Meta:
        db_table = "sites_theme"
        verbose_name = "主题模板"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Site(models.Model):
    """单个站点 — 一个域名 + 一套主题 + 一组配置。"""

    host = models.CharField("域名", max_length=255, unique=True, db_index=True)
    name = models.CharField("站名", max_length=128)
    theme = models.ForeignKey(Theme, on_delete=models.PROTECT, related_name="sites")
    is_active = models.BooleanField("启用", default=True)

    # TDK
    site_title = models.CharField("首页标题", max_length=255)
    site_description = models.TextField("首页描述", blank=True)
    site_keywords = models.CharField("首页关键词", max_length=255, blank=True)
    logo = models.URLField("Logo URL", blank=True)
    favicon = models.URLField("Favicon URL", blank=True)

    # SEO / GEO
    robots_txt = models.TextField("robots.txt", blank=True)
    sitemap_enabled = models.BooleanField("Sitemap", default=True)
    geo_region = models.CharField("GEO地区", max_length=64, blank=True)
    geo_lang = models.CharField("GEO语言", max_length=16, default="zh-CN")
    canonical_domain = models.CharField("canonical 域名", max_length=255, blank=True)

    # 偏移量：书籍列表起始位置，使不同站列表错位展示
    offset = models.IntegerField("偏移量", default=0, help_text="书籍列表起始位置，避免站间内容完全重复")

    # 主题自定义配置（合并自 theme.default_config）
    theme_config = models.JSONField("主题配置", default=dict, blank=True)

    # 站点 SEO 内容注入
    head_inject = models.TextField("Head 注入代码", blank=True, help_text="在 <head> 末尾注入")
    body_inject = models.TextField("Body 注入代码", blank=True, help_text="在 </body> 前注入")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sites_site"
        verbose_name = "站点"
        verbose_name_plural = verbose_name
        ordering = ("host",)

    def __str__(self) -> str:
        return f"{self.name} ({self.host})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate site cache
        try:
            cache.delete(f"site:{self.host}")
            cache.delete("site:all")
        except Exception:
            pass

    @classmethod
    def get_by_host(cls, host: str) -> "Site | None":
        cache_key = f"site:{host}"
        site = cache.get(cache_key)
        if site is None:
            site = cls.objects.filter(host=host, is_active=True).first()
            if site:
                cache.set(cache_key, site, 300)
        return site


# v49: Re-export ABTestConfig for model discovery

# v63: Re-export PageView

# v70: Re-export AdSlot
