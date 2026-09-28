"""Obfuscator models — per-site obfuscation profile + transcode maps + synonym dict + interference sentences.

The obfuscation engine has 3 layers:
  1. HTML structure obfuscation — every page render produces structurally unique HTML
     that looks identical visually. Combats content-fingerprint detection.
  2. Text transcoding — transforms visible text in ways that preserve readability but
     change bytes (full/half width, homoglyphs, zero-width chars, punctuation variants).
     Combats keyword-based audit/review mechanisms.
  3. Pseudo-original rewriting — synonym replacement + sentence restructure +
     interference sentence insertion. Produces per-page unique paragraph fingerprints.
"""
from __future__ import annotations

from django.db import models


class ObfuscationProfile(models.Model):
    """Per-site obfuscation profile.

    Bound to a Site via `site` FK. Each Site can have one profile.
    """

    site = models.OneToOneField(
        "sites.Site", on_delete=models.CASCADE, related_name="obfuscation_profile"
    )
    enabled = models.BooleanField("启用混淆", default=False)

    # ── Layer 1: HTML structure ──────────────────────────────
    html_class_randomize = models.BooleanField("类名随机化", default=True,
        help_text="每次渲染生成随机 class 名映射")
    html_attr_order_shuffle = models.BooleanField("属性顺序随机", default=True)
    html_whitespace_noise = models.BooleanField("空白噪声", default=True,
        help_text="随机插入 HTML 注释 / 空白字符")
    html_invisible_elements = models.BooleanField("隐形元素", default=True,
        help_text="随机插入 display:none 的 div/span")
    html_comment_inject = models.BooleanField("注释噪声", default=True,
        help_text="随机插入 HTML 注释片段")

    # ── Layer 2: Text transcoding ───────────────────────────
    transcode_full_width = models.BooleanField("半角→全角", default=False,
        help_text="随机将半角字符转为全角（视觉相同，字节不同）")
    transcode_homoglyph = models.BooleanField("同形字替换", default=False,
        help_text="替换拉丁字母为西里尔字母等 Unicode 同形字符")
    transcode_zero_width = models.BooleanField("零宽字符", default=False,
        help_text="在字符间随机插入零宽字符（ZWS / ZWNJ 等）")
    transcode_punctuation = models.BooleanField("标点变体", default=True,
        help_text="标点符号替换为 Unicode 等价变体")
    transcode_density = models.FloatField("转码密度", default=0.15,
        help_text="0.0~1.0，每个字符被转码的概率")

    # ── Layer 3: Pseudo-original rewriting ──────────────────
    rewrite_synonym = models.BooleanField("同义词替换", default=False,
        help_text="根据同义词词典随机替换")
    rewrite_sentence_reorder = models.BooleanField("句型重排", default=False,
        help_text="前后子句互换、副词位置调整")
    rewrite_interference = models.BooleanField("干扰句插入", default=False,
        help_text="在每个段落尾部插入一句干扰句子")
    rewrite_interference_density = models.FloatField("干扰句密度", default=0.3,
        help_text="0.0~1.0，每个段落插入干扰句的概率")

    # ── Cache control ───────────────────────────────────────
    cache_seconds = models.IntegerField("渲染缓存秒数", default=0,
        help_text="0 = 不缓存（每次渲染都生成唯一结构），>0 = 缓存 N 秒")
    seed_per_request = models.BooleanField("每请求重新生成种子", default=True,
        help_text="True: 每个请求生成不同结构；False: 同一站点固定结构（开发用）")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "obfuscator_profile"
        verbose_name = "混淆配置"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return f"混淆配置 ({self.site.host})"


class Synonym(models.Model):
    """Synonym dictionary — used by rewrite_synonym layer."""

    word = models.CharField("原词", max_length=64, db_index=True)
    synonyms = models.JSONField("同义词列表", default=list, help_text='["替换词1","替换词2"]')
    category = models.CharField("分类", max_length=32, blank=True, default="general",
        help_text="general / verb / noun / adj / adv")
    enabled = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "obfuscator_synonym"
        verbose_name = "同义词"
        verbose_name_plural = verbose_name
        unique_together = ("word", "category")

    def __str__(self) -> str:
        return f"{self.word} → {self.synonyms}"


class InterferenceSentence(models.Model):
    """干扰句库 — 可插入正文段落，增加内容伪原创性。"""

    text = models.TextField("句子内容")
    category = models.CharField("分类", max_length=32, default="general",
        help_text="general / scene / dialogue / narration")
    weight = models.FloatField("权重", default=1.0)
    enabled = models.BooleanField("启用", default=True)
    used_count = models.IntegerField("已用次数", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "obfuscator_interference"
        verbose_name = "干扰句"
        verbose_name_plural = verbose_name
        ordering = ("-weight", "id")

    def __str__(self) -> str:
        return self.text[:60]


class RewriteRecord(models.Model):
    """伪原创记录 — 用于指纹去重。

    每次对一段文本做重写后，将原文哈希 + 重写哈希存储，
    下次再遇相同原文时换一组变换组合，避免重复。
    """

    original_hash = models.CharField("原文哈希", max_length=64, db_index=True)
    rewritten_hash = models.CharField("重写哈希", max_length=64, db_index=True)
    transformations = models.JSONField("使用的变换", default=list,
        help_text='["synonym:word1->word2", "reorder", "interference:id=12"]')
    site = models.ForeignKey("sites.Site", on_delete=models.SET_NULL, null=True, blank=True)
    book = models.ForeignKey("novel.Book", on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey("novel.Chapter", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "obfuscator_rewrite_record"
        verbose_name = "重写记录"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["original_hash", "site"]),
        ]

    def __str__(self) -> str:
        return f"{self.original_hash[:8]} → {self.rewritten_hash[:8]}"
