from django.contrib import admin

from .models import CrawlerRule, CrawlerSource


@admin.register(CrawlerSource)
class CrawlerSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "host", "enabled", "rules_count", "created_at")
    list_filter = ("enabled",)
    search_fields = ("name", "host")

    def rules_count(self, obj):
        return obj.rules.count()


@admin.register(CrawlerRule)
class CrawlerRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "target", "source", "enabled", "priority", "last_test_at")
    list_filter = ("target", "enabled", "source")
    search_fields = ("name", "notes")
    readonly_fields = ("last_test_at",)
