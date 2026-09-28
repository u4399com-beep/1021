"""Ad slot management (v70) — manage ad placements across themes."""
from __future__ import annotations
from django.db import models


class AdSlot(models.Model):
    """A single ad placement definition."""
    SLOT_TYPES = (
        ("header_banner", "顶部横幅"),
        ("sidebar", "侧边栏"),
        ("footer_banner", "底部横幅"),
        ("chapter_top", "章节顶部"),
        ("chapter_bottom", "章节底部"),
        ("list_between", "列表中间"),
        ("popup", "弹窗"),
    )
    AD_FORMATS = (
        ("html", "HTML 代码"),
        ("image", "图片"),
        ("text", "纯文本"),
        ("adsense", "Google AdSense"),
    )
    name = models.CharField("广告位名", max_length=64, unique=True)
    slot_type = models.CharField("位置", max_length=32, choices=SLOT_TYPES, default="header_banner")
    ad_format = models.CharField("格式", max_length=16, choices=AD_FORMATS, default="html")
    content = models.TextField("广告内容", blank=True,
        help_text="HTML 代码 / 图片 URL / 文本 / AdSense 代码")
    image_url = models.URLField("图片URL", blank=True)
    link_url = models.URLField("跳转链接", blank=True)
    width = models.IntegerField("宽度(px)", default=0, help_text="0=自适应")
    height = models.IntegerField("高度(px)", default=0, help_text="0=自适应")
    
    # Targeting
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="ad_slots", null=True, blank=True)
    theme = models.CharField("适用主题", max_length=32, blank=True, help_text="留空=所有主题")
    page_types = models.JSONField("页面类型", default=list, help_text='["home","book","chapter"]')
    
    # Display control
    is_active = models.BooleanField("启用", default=True)
    display_probability = models.FloatField("展示概率", default=1.0, help_text="0.0-1.0")
    start_at = models.DateTimeField("开始时间", null=True, blank=True)
    end_at = models.DateTimeField("结束时间", null=True, blank=True)
    
    # Stats
    impression_count = models.BigIntegerField("展示次数", default=0)
    click_count = models.BigIntegerField("点击次数", default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sites_ad_slot"
        verbose_name = "广告位"
        verbose_name_plural = verbose_name
        ordering = ("slot_type", "-id")

    def __str__(self): return self.name
    
    @property
    def ctr(self):
        total = self.impression_count or 1
        return round(self.click_count / total * 100, 2)


def get_ads_for_page(site_host: str, page_type: str, theme: str = "") -> list[dict]:
    """Return active ads matching the given page context."""
    from django.utils import timezone
    now = timezone.now()
    qs = AdSlot.objects.filter(is_active=True)
    # Filter by site or global
    qs = qs.filter(models.Q(site__host=site_host) | models.Q(site__isnull=True))
    # Filter by page type
    matching = []
    for ad in qs:
        if ad.page_types and page_type not in ad.page_types:
            continue
        if ad.theme and theme and ad.theme != theme:
            continue
        if ad.start_at and now < ad.start_at:
            continue
        if ad.end_at and now > ad.end_at:
            continue
        matching.append({
            "name": ad.name, "slot_type": ad.slot_type,
            "ad_format": ad.ad_format, "content": ad.content,
            "image_url": ad.image_url, "link_url": ad.link_url,
            "width": ad.width, "height": ad.height,
        })
        ad.impression_count += 1
        ad.save(update_fields=["impression_count"])
    return matching
