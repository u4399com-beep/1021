"""文件下载配置 — 可定制内容插入（混淆、广告、站点信息）"""
from __future__ import annotations

from django.db import models


class DownloadTemplate(models.Model):
    """下载文件模板 — 描述如何插入混淆/广告/站点信息"""

    class OutputFormat(models.TextChoices):
        TXT = "txt", "TXT"
        EPUB = "epub", "EPUB"

    name = models.CharField("模板名", max_length=64, unique=True)
    output_format = models.CharField("输出格式", max_length=8, choices=OutputFormat.choices, default=OutputFormat.TXT)

    # Header / footer inserted at the top / bottom of each chapter
    chapter_header = models.TextField("章节头部插入", blank=True, default="")
    chapter_footer = models.TextField("章节尾部插入", blank=True, default="")

    # Book-level inserts
    book_preface = models.TextField("前言插入", blank=True, default="")
    book_afterword = models.TextField("后记插入", blank=True, default="")

    # Site info / ad block (multilingual supported via {site_name} etc.)
    site_info_block = models.TextField("站点信息块", blank=True, default="")
    ad_block = models.TextField("广告块", blank=True, default="")

    # Confusion / 混淆 — random unicode filler to defeat similarity detection
    enable_confusion = models.BooleanField("启用混淆", default=False)
    confusion_density = models.FloatField("混淆密度", default=0.01, help_text="0.001~0.05 推荐范围")
    confusion_chars = models.TextField("混淆字符集", blank=True, default="\u200b\u200c\u200d\ufeff")

    enabled = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "download_template"
        verbose_name = "下载模板"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return f"[{self.get_output_format_display()}] {self.name}"


class DownloadRecord(models.Model):
    """每次下载任务的执行记录"""

    template = models.ForeignKey(DownloadTemplate, on_delete=models.SET_NULL, null=True)
    book = models.ForeignKey("novel.Book", on_delete=models.CASCADE, related_name="downloads")
    output_format = models.CharField("格式", max_length=8)
    file_path = models.CharField("文件路径", max_length=512)
    file_size = models.BigIntegerField("文件大小", default=0)
    chapters_count = models.IntegerField("章节数", default=0)
    created_by = models.ForeignKey("account.User", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "download_record"
        verbose_name = "下载记录"
        verbose_name_plural = verbose_name
        ordering = ("-id",)
