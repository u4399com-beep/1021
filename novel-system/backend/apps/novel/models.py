"""Novel core models — Book, Category, Chapter, Tag, Author, SuggestKeyword.

Design notes
------------
* `Book.slug` — used as the main keyword anchor for SEO/GEO.
  Search-engine suggestion keywords (`SuggestKeyword`) point back to it.
* `Chapter.source_url` — unique per (book, source_url) for idempotent crawl.
* `Chapter.status` — `pending` / `fetched` / `cleaned` / `published`.
* Soft-delete via `is_deleted` to support incremental updates without losing history.
"""
from __future__ import annotations

from django.db import models
from django.utils.text import slugify


class Author(models.Model):
    name = models.CharField("作者名", max_length=128, db_index=True)
    alias = models.JSONField("作者别名", default=list, blank=True)
    source_url = models.URLField("作者页地址", blank=True)
    intro = models.TextField("作者简介", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "novel_author"
        unique_together = ("name", "source_url")
        verbose_name = "作者"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    """Two-level taxonomy: parent + child."""

    name = models.CharField("分类名", max_length=64, db_index=True)
    slug = models.SlugField("别名", max_length=128, unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    cover = models.URLField("分类封面", blank=True)
    intro = models.TextField("简介", blank=True)
    order = models.IntegerField("排序", default=0)
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        db_table = "novel_category"
        verbose_name = "分类"
        verbose_name_plural = verbose_name
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField("标签", max_length=64, unique=True)
    is_auto = models.BooleanField("自动生成", default=False)
    suggest_source = models.CharField("来源建议词", max_length=64, blank=True)

    class Meta:
        db_table = "novel_tag"
        verbose_name = "标签"
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    """Main novel entity."""

    class Status(models.TextChoices):
        ONGOING = "ongoing", "连载中"
        COMPLETED = "completed", "已完结"
        UNKNOWN = "unknown", "未知"

    title = models.CharField("书名", max_length=255, db_index=True)
    slug = models.SlugField("URL别名", max_length=255, unique=True)
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True, related_name="books")
    categories = models.ManyToManyField(Category, related_name="books", blank=True)
    tags = models.ManyToManyField(Tag, related_name="books", blank=True)

    cover = models.ImageField("封面图", upload_to="uploads/covers/%Y/%m/", blank=True, null=True)
    cover_url = models.URLField("原始封面URL", blank=True)

    intro = models.TextField("简介", blank=True)
    keywords = models.JSONField("关键词", default=list, blank=True)
    word_count = models.BigIntegerField("字数", default=0)
    chapter_count = models.IntegerField("章节数", default=0)
    volume_count = models.IntegerField("分卷数", default=0, help_text="自动计算")

    status = models.CharField("状态", max_length=16, choices=Status.choices, default=Status.ONGOING)
    finished_at = models.DateTimeField("完结时间", null=True, blank=True)
    last_chapter_title = models.CharField("最新章节标题", max_length=255, blank=True)

    rating = models.FloatField("评分", default=0)
    view_count = models.BigIntegerField("浏览量", default=0)

    source_site = models.CharField("采集源域名", max_length=255, blank=True)
    source_url = models.URLField("源书籍页URL", blank=True, db_index=True)
    source_book_id = models.CharField("源书籍ID", max_length=128, blank=True)

    is_published = models.BooleanField("是否发布", default=True)
    is_deleted = models.BooleanField("软删除", default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "novel_book"
        verbose_name = "书籍"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["status", "is_published"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["author", "status"]),
            # Performance indexes added in v11
            models.Index(fields=["slug", "is_published"]),
            models.Index(fields=["-rating"]),
            models.Index(fields=["-updated_at"]),
            models.Index(fields=["source_site", "is_deleted"]),
            models.Index(fields=["finished_at"]),
            # Composite index for typical "list by status + sort by rating" queries
            models.Index(fields=["status", "is_published", "-rating"], name="book_status_rating_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} / {self.author or '-'}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def update_volume_count(self):
        """Recalculate the volume_count field."""
        self.volume_count = self.volumes.count()
        self.save(update_fields=["volume_count"])

    def update_chapter_count(self):
        """Recalculate the chapter_count field."""
        self.chapter_count = self.chapters.count()
        self.save(update_fields=["chapter_count"])


class Volume(models.Model):
    """A volume (分卷) — groups chapters within a book.

    A book can have many volumes, each with many chapters. The disorder
    reordering feature respects volume boundaries: chapters are first sorted
    by (volume.order_index, chapter.order_index), so even when chapters are
    shuffled, they remain within their volume.
    """

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="volumes")
    name = models.CharField("卷名", max_length=128, help_text="例：第一卷 初出茅庐")
    intro = models.TextField("卷简介", blank=True)
    order_index = models.IntegerField("卷序号", default=0, db_index=True,
        help_text="第几卷，从 1 开始")
    source_id = models.CharField("源分卷ID", max_length=128, blank=True)
    chapter_count = models.IntegerField("章节计数", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "novel_volume"
        verbose_name = "分卷"
        verbose_name_plural = verbose_name
        unique_together = [("book", "order_index"), ("book", "name")]
        ordering = ("order_index", "id")
        indexes = [
            models.Index(fields=["book", "order_index"]),
        ]

    def __str__(self) -> str:
        return f"{self.book.title} - {self.name}"

    def update_chapter_count(self):
        self.chapter_count = self.chapters.count()
        self.save(update_fields=["chapter_count"])


class Chapter(models.Model):
    """Chapter of a book.

    `order_index` — display order.  When `disorder_applied` is True the order has
    been intentionally shuffled for the front (anti-duplicate-content SEO trick).
    The original order is preserved in `source_order`.

    Volume: when `volume` is set, the chapter belongs to a Volume. The disorder
    reordering respects volume boundaries — chapters shuffle WITHIN their volume
    only, never across volumes. See `apps.crawler_engine.pipeline._disorder`.
    """

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    volume = models.ForeignKey(
        "Volume", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="chapters", help_text="所属分卷"
    )
    title = models.CharField("标题", max_length=255)
    order_index = models.IntegerField("排序", db_index=True)
    source_order = models.IntegerField("原始排序", default=0)
    disorder_applied = models.BooleanField("乱序重排", default=False)

    content = models.TextField("正文", blank=True)
    word_count = models.IntegerField("字数", default=0)

    source_url = models.URLField("源章节URL", blank=True)
    source_id = models.CharField("源章节ID", max_length=128, blank=True)
    source_paged = models.BooleanField("是否分页", default=False)
    source_page_count = models.IntegerField("分页数", default=1)

    status = models.CharField(
        "状态",
        max_length=16,
        choices=[("pending", "待采集"), ("fetched", "已采集"), ("cleaned", "已清洗"), ("published", "已发布"), ("error", "失败")],
        default="pending",
    )
    error_msg = models.TextField("错误信息", blank=True)
    fetched_at = models.DateTimeField("采集时间", null=True, blank=True)

    # Optional on-disk storage (txt) — set when content_storage = "txt"
    txt_path = models.CharField("TXT路径", max_length=512, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "novel_chapter"
        verbose_name = "章节"
        verbose_name_plural = verbose_name
        unique_together = [("book", "source_url"), ("book", "title", "order_index")]
        ordering = ("order_index", "id")
        indexes = [
            models.Index(fields=["book", "status"]),
            models.Index(fields=["book", "order_index"]),
        ]

    def __str__(self) -> str:
        return f"{self.book.title} #{self.order_index} {self.title}"


class SuggestKeyword(models.Model):
    """Keyword pulled from search-engine autocomplete.

    `main_slug` points to the master Book.slug. The keyword URL is exposed on
    the front-end and redirects to the main book page (for SEO consolidation).
    """

    keyword = models.CharField("关键词", max_length=128, db_index=True)
    main_book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="suggest_keywords")
    main_slug = models.SlugField("主书籍slug", max_length=255, db_index=True)
    source = models.CharField("来源引擎", max_length=32)
    weight = models.IntegerField("权重", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "novel_suggest_keyword"
        verbose_name = "搜索引擎建议词"
        verbose_name_plural = verbose_name
        unique_together = ("keyword", "source")

    def __str__(self) -> str:
        return f"{self.keyword} ({self.source}) → {self.main_slug}"

# v80: Re-export BookRating
from .ratings import BookRating  # noqa: E402
