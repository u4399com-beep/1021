from django.contrib import admin

from .models import CrawlerTask, CrawlerTaskLog


@admin.register(CrawlerTask)
class CrawlerTaskAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "mode", "enabled", "total_items", "success_items", "started_at")
    list_filter = ("status", "mode", "enabled")
    search_fields = ("name", "notes")
    filter_horizontal = ()
    readonly_fields = (
        "celery_task_id", "total_items", "processed_items", "success_items",
        "failed_items", "skipped_items", "started_at", "finished_at", "last_error",
    )


@admin.register(CrawlerTaskLog)
class CrawlerTaskLogAdmin(admin.ModelAdmin):
    list_display = ("task", "level", "message", "url", "created_at")
    list_filter = ("level",)
    search_fields = ("message", "url")
    readonly_fields = ("task", "level", "message", "url", "payload", "created_at")
