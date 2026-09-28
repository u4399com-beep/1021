"""Webhook API — CRUD + test dispatch."""
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.account.permissions import CanEditSystem

from .engine import dispatch_event
from .models import WebhookDelivery, WebhookEndpoint
from .serializers import WebhookDeliverySerializer, WebhookEndpointSerializer


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    queryset = WebhookEndpoint.objects.all()
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsAuthenticated, CanEditSystem]
    filterset_fields = ("enabled", "provider")
    search_fields = ("name", "notes")
    ordering = ("name",)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Send a test event to this endpoint."""
        ep = self.get_object()
        result = dispatch_event("task.done", {
            "name": "[TEST] 测试任务",
            "success": 10, "failed": 0, "skipped": 0,
        })
        return Response({
            "endpoint_id": ep.id, "endpoint_name": ep.name,
            "sent": result["sent"], "deliveries": result["deliveries"],
        })

    @action(detail=True, methods=["get"])
    def deliveries(self, request, pk=None):
        """List recent deliveries for this endpoint."""
        ep = self.get_object()
        qs = ep.deliveries.all()[:50]
        return Response(WebhookDeliverySerializer(qs, many=True).data)


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookDelivery.objects.all()
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated, CanEditSystem]
    filterset_fields = ("endpoint", "event", "success")
    ordering = ("-sent_at",)


class WebhookEventViewSet(viewsets.ViewSet):
    """Event catalog + manual dispatch."""

    @action(detail=False, methods=["get"], url_path="catalog")
    def catalog(self, request):
        from .engine import EVENT_TEMPLATES
        return Response({
            "events": [
                {"event": k, "template": v}
                for k, v in EVENT_TEMPLATES.items()
            ],
        })

    @action(detail=False, methods=["post"], url_path="dispatch")
    def dispatch(self, request):
        """Manually dispatch an event."""
        event = request.data.get("event", "task.done")
        context = request.data.get("context", {})
        result = dispatch_event(event, context)
        return Response({"event": event, **result})
