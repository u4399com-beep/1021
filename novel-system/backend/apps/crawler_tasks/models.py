"""采集任务模型。

设计要点：
- 一个任务绑定一组规则 + 一个目标 URL 或 URL 范围
- 任务有完整的生命周期：draft → queued → running → paused → stopped → done → error
- 任务执行参数：threads_min/threads_max, interval_min/max, mode(full/incremental)
- 任务进度记录：已采集 URL 数 / 失败数 / 跳过数
- 每次运行产生一个 TaskRun 记录，便于多次重试历史追溯
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.crawler_rules.models import CrawlerRule


class CrawlerTask(models.Model):
    """采集任务定义。"""

    class Mode(models.TextChoices):
        FULL = "full", "完全覆盖"
        INCREMENTAL = "incremental", "增量更新"

    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        QUEUED = "queued", "已入队"
        RUNNING = "running", "运行中"
        PAUSED = "paused", "已暂停"
        STOPPED = "stopped", "已停止"
        DONE = "done", "完成"
        ERROR = "error", "失败"

    name = models.CharField("任务名", max_length=128)
    enabled = models.BooleanField("启用", default=True)

    # 规则绑定
    list_rule = models.ForeignKey(
        CrawlerRule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks_as_list", limit_choices_to={"target": "list"},
    )
    book_rule = models.ForeignKey(
        CrawlerRule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks_as_book", limit_choices_to={"target": "book"},
    )
    toc_rule = models.ForeignKey(
        CrawlerRule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks_as_toc", limit_choices_to={"target": "toc"},
    )
    chapter_rule = models.ForeignKey(
        CrawlerRule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks_as_chapter", limit_choices_to={"target": "chapter"},
    )

    # URL 范围
    target_urls = models.JSONField("目标URL列表", default=list, help_text="单本/多本URL数组")
    url_range = models.JSONField(
        "URL范围配置", default=dict, blank=True,
        help_text="支持分页范围 / 章节范围，例 {start:1,end:100,step:1}",
    )

    # 执行参数
    mode = models.CharField("模式", max_length=16, choices=Mode.choices, default=Mode.FULL)
    threads_min = models.IntegerField("最小线程", default=2)
    threads_max = models.IntegerField("最大线程", default=5)
    interval_min = models.FloatField("最小间隔(秒)", default=1.0)
    interval_max = models.FloatField("最大间隔(秒)", default=3.0)

    # 输出选项
    content_storage = models.CharField(
        "章节内容存储方式",
        max_length=8,
        choices=[("db", "数据库"), ("txt", "TXT文件"), ("both", "两者")],
        default="db",
    )
    cover_format = models.CharField("封面格式", max_length=8, default="webp")
    download_cover = models.BooleanField("下载封面", default=True)

    # 智能选项
    enable_disorder = models.BooleanField("章节乱序重排", default=False)
    enable_dedup_by_url = models.BooleanField("按URL去重", default=True)
    enable_dedup_by_title = models.BooleanField("按章节名去重", default=False)
    enable_cleaner = models.BooleanField("启用内容清洗", default=True)
    enable_classifier = models.BooleanField("启用智能分类", default=True)
    enable_finished_detection = models.BooleanField("完结检测", default=True)

    # 状态机
    status = models.CharField("状态", max_length=16, choices=Status.choices, default=Status.DRAFT)
    celery_task_id = models.CharField("Celery Task ID", max_length=128, blank=True)

    # 进度统计
    total_items = models.IntegerField("总数", default=0)
    processed_items = models.IntegerField("已处理", default=0)
    success_items = models.IntegerField("成功", default=0)
    failed_items = models.IntegerField("失败", default=0)
    skipped_items = models.IntegerField("跳过", default=0)

    started_at = models.DateTimeField("开始时间", null=True, blank=True)
    finished_at = models.DateTimeField("结束时间", null=True, blank=True)
    last_error = models.TextField("最近错误", blank=True)

    notes = models.TextField("备注", blank=True)
    created_by = models.ForeignKey(
        "account.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="crawler_tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crawler_task"
        verbose_name = "采集任务"
        verbose_name_plural = verbose_name
        ordering = ("-id",)
        indexes = [
            models.Index(fields=["status", "enabled"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.get_status_display()}] {self.name}"

    # --- lifecycle helpers ---
    def mark_running(self, celery_id: str):
        self.status = self.Status.RUNNING
        self.celery_task_id = celery_id
        self.started_at = timezone.now()
        self.save(update_fields=["status", "celery_task_id", "started_at"])

    def mark_paused(self):
        self.status = self.Status.PAUSED
        self.save(update_fields=["status"])

    def mark_stopped(self):
        self.status = self.Status.STOPPED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    def mark_done(self):
        self.status = self.Status.DONE
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    def mark_error(self, err: str):
        self.status = self.Status.ERROR
        self.last_error = err
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "last_error", "finished_at"])

    def inc_progress(self, *, processed=0, success=0, failed=0, skipped=0):
        CrawlerTask.objects.filter(pk=self.pk).update(
            processed_items=models.F("processed_items") + processed,
            success_items=models.F("success_items") + success,
            failed_items=models.F("failed_items") + failed,
            skipped_items=models.F("skipped_items") + skipped,
        )


class CrawlerTaskLog(models.Model):
    """每次任务的运行日志条目。"""

    task = models.ForeignKey(CrawlerTask, on_delete=models.CASCADE, related_name="logs")
    level = models.CharField("级别", max_length=8, default="info")
    message = models.TextField("日志内容")
    url = models.URLField("相关URL", blank=True)
    payload = models.JSONField("附加数据", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "crawler_task_log"
        verbose_name = "采集任务日志"
        verbose_name_plural = verbose_name
        ordering = ("-id",)

    def __str__(self) -> str:
        return f"[{self.level}] {self.task.name}: {self.message[:50]}"
