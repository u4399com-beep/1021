from django.contrib import admin

from .models import DownloadRecord, DownloadTemplate


@admin.register(DownloadTemplate)
class DownloadTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "output_format", "enable_confusion", "enabled")
    list_filter = ("output_format", "enabled")
    search_fields = ("name",)


@admin.register(DownloadRecord)
class DownloadRecordAdmin(admin.ModelAdmin):
    list_display = ("book", "output_format", "file_size", "chapters_count", "created_by", "created_at")
    list_filter = ("output_format",)
    readonly_fields = ("created_at", "file_path", "file_size")
