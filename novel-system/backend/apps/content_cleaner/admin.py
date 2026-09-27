from django.contrib import admin

from .models import CleaningExecution, CleaningRule


@admin.register(CleaningRule)
class CleaningRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "target", "strategy", "priority", "enabled")
    list_filter = ("target", "strategy", "enabled")
    search_fields = ("name", "pattern")
    ordering = ("priority", "id")


@admin.register(CleaningExecution)
class CleaningExecutionAdmin(admin.ModelAdmin):
    list_display = ("rule", "target_type", "target_id", "changed", "before_size", "after_size", "executed_at")
    list_filter = ("target_type", "changed")
    readonly_fields = ("executed_at",)
