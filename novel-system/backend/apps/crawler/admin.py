from django.contrib import admin

from .models import ProxyPool


@admin.register(ProxyPool)
class ProxyPoolAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "proxy_type", "region", "is_active",
                    "priority", "success_count", "failure_count",
                    "last_check_ok", "last_used_at")
    list_filter = ("is_active", "proxy_type", "last_check_ok")
    search_fields = ("name", "url", "region", "notes")
    readonly_fields = ("success_count", "failure_count", "last_used_at", "last_check_at", "last_check_ok")
    actions = ["mark_active", "mark_inactive"]

    def mark_active(self, request, qs):
        qs.update(is_active=True)
    mark_active.short_description = "启用选中代理"

    def mark_inactive(self, request, qs):
        qs.update(is_active=False)
    mark_inactive.short_description = "禁用选中代理"
