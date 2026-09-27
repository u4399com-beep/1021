"""智能分类模型 — 分类映射 + 训练样本。

实际分类逻辑在 engine.py 用 jieba 分词 + 关键词匹配 + sklearn TF-IDF 兜底。
"""
from __future__ import annotations

from django.db import models


class CategoryKeyword(models.Model):
    """分类关键词 — 命中越多则越可能属于此分类。"""

    category_name = models.CharField("分类名", max_length=64, db_index=True)
    keyword = models.CharField("关键词", max_length=64, db_index=True)
    weight = models.FloatField("权重", default=1.0)

    class Meta:
        db_table = "classifier_category_keyword"
        verbose_name = "分类关键词"
        verbose_name_plural = verbose_name
        unique_together = ("category_name", "keyword")

    def __str__(self) -> str:
        return f"{self.category_name} ← {self.keyword} ({self.weight})"


class FinishedPattern(models.Model):
    """完结判断模式 — 命中则视作已完结。"""

    name = models.CharField("规则名", max_length=64, unique=True)
    pattern = models.CharField("正则", max_length=255, help_text="应用到标题/简介/最近章节标题")
    enabled = models.BooleanField("启用", default=True)
    priority = models.IntegerField("优先级", default=100)

    class Meta:
        db_table = "classifier_finished_pattern"
        verbose_name = "完结规则"
        verbose_name_plural = verbose_name
        ordering = ("priority", "id")
