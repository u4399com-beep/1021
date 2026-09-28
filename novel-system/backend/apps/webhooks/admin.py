from django.contrib import admin

from .models import WebhookDelivery, WebhookEndpoint


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "enabled", "events_count",
                    "sent_count", "fail_count", "last_sent_at")
    list_filter = ("enabled", "provider")
    search_fields = ("name", "notes")
    readonly_fields = ("sent_count", "fail_count", "last_sent_at", "last_error")

    def events_count(self, obj):
        return len(obj.events or [])


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "event", "success", "status_code", "duration_ms", "sent_at")
    list_filter = ("event", "success", "endpoint")
    readonly_fields = ("endpoint", "event", "payload", "status_code",
                       "response_text", "success", "error", "duration_ms", "sent_at")
