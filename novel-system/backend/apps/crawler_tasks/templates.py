"""Crawler task templates (v43) — save common task configs for one-click reuse."""
import json
from django.db import models
from apps.crawler_tasks.models import CrawlerTask


class TaskTemplate(models.Model):
    """A reusable task configuration template."""
    name = models.CharField("模板名", max_length=128, unique=True)
    description = models.TextField("描述", blank=True)
    config = models.JSONField("配置", default=dict,
        help_text="任务字段快照，用于创建新任务")
    is_builtin = models.BooleanField("内置", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crawler_task_template"
        verbose_name = "任务模板"
        verbose_name_plural = verbose_name
        ordering = ("name",)

    def __str__(self): return self.name

    @classmethod
    def from_task(cls, task: CrawlerTask, name: str, description: str = "") -> "TaskTemplate":
        """Snapshot a task's config into a template."""
        config = {
            "mode": task.mode, "threads_min": task.threads_min,
            "threads_max": task.threads_max, "interval_min": task.interval_min,
            "interval_max": task.interval_max, "content_storage": task.content_storage,
            "cover_format": task.cover_format, "download_cover": task.download_cover,
            "enable_disorder": task.enable_disorder,
            "enable_dedup_by_url": task.enable_dedup_by_url,
            "enable_dedup_by_title": task.enable_dedup_by_title,
            "enable_cleaner": task.enable_cleaner,
            "enable_classifier": task.enable_classifier,
            "enable_finished_detection": task.enable_finished_detection,
            "priority": task.priority,
            "retry_max": task.retry_max, "retry_delay": task.retry_delay,
            "retry_strategy": task.retry_strategy,
        }
        return cls.objects.create(name=name, description=description, config=config)

    def create_task(self, **overrides) -> CrawlerTask:
        """Create a new task from this template."""
        config = dict(self.config)
        config.update(overrides)
        return CrawlerTask.objects.create(name=config.pop("name", f"from_{self.name}"), **config)
