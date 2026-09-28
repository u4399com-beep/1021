from django.contrib import admin

from .models import AuditEntry
from .views import AuditEntryViewSet  # noqa — just to keep the import for apps loading


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "username", "action", "resource", "resource_id",
                    "method", "path", "status_code", "duration_ms", "success")
    list_filter = ("action", "resource", "success", "method")
    search_fields = ("username", "path", "resource", "resource_id", "error")
    readonly_fields = ("created_at", "user_id", "username", "action", "resource",
                       "resource_id", "method", "path", "ip", "user_agent",
                       "payload", "status_code", "success", "error", "duration_ms")
    ordering = ("-id",)
