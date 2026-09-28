"""采集规则模型 — 支持正则 / CSS / XPath 三种解析器同时使用。

设计要点：
- 一条规则对应一个采集源站点 + 一个采集目标类型 (列表/书籍/目录/章节内容)
- 每条规则的 selector 可以指定 type: regex | css | xpath
- 规则字段全部用 JSONField，便于编辑（前端做结构化编辑器）
- 内置"测试快照"功能：保留最近一次测试的 HTML 和解析结果
"""
from __future__ import annotations

from django.db import models


SELECTOR_TYPES = (
    ("regex", "正则表达式"),
    ("css", "CSS Selector"),
    ("xpath", "XPath"),
    ("json_path", "JSONPath"),
)

TARGET_TYPES = (
    ("list", "列表页"),
    ("book", "书籍信息页"),
    ("toc", "章节目录页"),
    ("chapter", "章节内容页"),
)


class CrawlerSource(models.Model):
    """采集源站点。

    一个源站点对应一个域名，下面挂多条规则。
    """

    name = models.CharField("名称", max_length=64, unique=True)
    host = models.CharField("域名", max_length=255, unique=True, db_index=True)
    enabled = models.BooleanField("启用", default=True)
    anti_detection = models.JSONField("反反爬配置", default=dict, blank=True)
    notes = models.TextField("备注", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crawler_source"
        verbose_name = "采集源"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return self.name


class CrawlerRule(models.Model):
    """采集规则。

    `config` 字段结构示例（target=list 时）::

        {
          "url_pattern": "https://www.example.com/list/{{page}}.html",
          "pagination": {"enabled": true, "start": 1, "end": 100, "step": 1},
          "item_selector": {
            "type": "css",
            "expr": "div.book-list > ul > li"
          },
          "book_url": {"type": "xpath", "expr": ".//a/@href"},
          "book_title": {"type": "css", "expr": "h3.title::text"},
          "book_author": {"type": "css", "expr": "span.author::text"}
        }
    """

    name = models.CharField("规则名", max_length=128)
    source = models.ForeignKey(
        CrawlerSource, on_delete=models.CASCADE, related_name="rules", null=True, blank=True
    )
    target = models.CharField("目标类型", max_length=16, choices=TARGET_TYPES, db_index=True)

    enabled = models.BooleanField("启用", default=True)
    priority = models.IntegerField("优先级", default=100)

    # JSON config — see docstring for structure
    config = models.JSONField("规则配置", default=dict)

    # Test snapshot — keeps the last HTML + parsed result
    last_test_html = models.TextField("最近测试HTML", blank=True)
    last_test_result = models.JSONField("最近测试结果", default=dict, blank=True)
    last_test_at = models.DateTimeField("最近测试时间", null=True, blank=True)

    notes = models.TextField("备注", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crawler_rule"
        verbose_name = "采集规则"
        verbose_name_plural = verbose_name
        ordering = ("priority", "id")
        indexes = [
            models.Index(fields=["source", "target", "enabled"]),
            models.Index(fields=["target"]),
        ]

    def __str__(self) -> str:
        return f"[{self.get_target_display()}] {self.name}"

    # --------------------------------------------------------------
    # Helpers for serializing selector types to front-end editor
    # --------------------------------------------------------------
    def to_editor_payload(self) -> dict:
        """Return a structured payload for the front-end rule editor."""
        return {
            "id": self.id,
            "name": self.name,
            "source_id": self.source_id,
            "target": self.target,
            "enabled": self.enabled,
            "priority": self.priority,
            "config": self.config,
            "notes": self.notes,
            "last_test_at": self.last_test_at,
            "last_test_result": self.last_test_result,
        }

# v57: Re-export RuleVersion
from .versioning import RuleVersion  # noqa: E402
