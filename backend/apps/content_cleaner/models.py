"""内容清洗配置 — 规则集 + 应用入口。

清洗规则可以匹配 HTML 片段、文本片段、关键词列表，匹配到的内容会被替换/移除。
"""
from __future__ import annotations

from django.db import models


class CleaningRule(models.Model):
    """清洗规则 — 按优先级执行。"""

    class Target(models.TextChoices):
        CHAPTER = "chapter", "章节正文"
        BOOK = "book", "书籍简介"
        AUTHOR = "author", "作者简介"
        ALL = "all", "全部"

    class Strategy(models.TextChoices):
        REGEX = "regex", "正则替换"
        CSS_REMOVE = "css_remove", "CSS 移除"
        XPATH_REMOVE = "xpath_remove", "XPath 移除"
        STRING_REMOVE = "string_remove", "字符串移除"
        STRING_REPLACE = "string_replace", "字符串替换"

    name = models.CharField("规则名", max_length=128, unique=True)
    target = models.CharField("目标", max_length=16, choices=Target.choices, default=Target.CHAPTER)
    strategy = models.CharField("策略", max_length=16, choices=Strategy.choices)
    pattern = models.TextField("匹配模式")
    replacement = models.TextField("替换为", blank=True, default="")
    priority = models.IntegerField("优先级", default=100)
    enabled = models.BooleanField("启用", default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cleaner_rule"
        verbose_name = "清洗规则"
        verbose_name_plural = verbose_name
        ordering = ("priority", "id")

    def __str__(self) -> str:
        return f"[{self.get_target_display()}/{self.get_strategy_display()}] {self.name}"


class CleaningExecution(models.Model):
    """清洗执行记录 — 用于审计与回滚。"""

    rule = models.ForeignKey(CleaningRule, on_delete=models.SET_NULL, null=True)
    target_type = models.CharField("目标类型", max_length=16)
    target_id = models.IntegerField("目标ID")
    before_size = models.IntegerField(default=0)
    after_size = models.IntegerField(default=0)
    changed = models.BooleanField("是否修改", default=False)
    diff_summary = models.TextField("变更摘要", blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cleaner_execution"
        verbose_name = "清洗记录"
        verbose_name_plural = verbose_name
        ordering = ("-executed_at",)


# v46: Re-export BannedKeyword for model discovery
from .audit import BannedKeyword  # noqa: E402
