"""Audit log serializers + views."""
from rest_framework import serializers, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AuditEntry


class AuditEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEntry
        fields = "__all__"


class AuditEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEntry.objects.all()
    serializer_class = AuditEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ("user_id", "username", "action", "resource", "success")
    ordering_fields = ("created_at", "duration_ms", "user_id")
    ordering = ("-id",)
    search_fields = ("username", "path", "resource", "error")

    @action(detail=False, methods=["get"])
    def by_user(self, request):
        """GET /audit/audit-entries/by_user/?user_id=1&limit=50"""
        uid = request.query_params.get("user_id")
        limit = int(request.query_params.get("limit", 50))
        if not uid:
            return Response({"error": "user_id required"}, status=400)
        qs = self.queryset.filter(user_id=uid)[:limit]
        return Response(AuditEntrySerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Aggregate stats: top users / actions / resources."""
        from django.db.models import Count
        # Top 10 users
        by_user = list(self.queryset.values("username").annotate(
            count=Count("id")
        ).order_by("-count")[:10])
        # By action
        by_action = list(self.queryset.values("action").annotate(
            count=Count("id")
        ).order_by("-count"))
        # By resource
        by_resource = list(self.queryset.values("resource").annotate(
            count=Count("id")
        ).order_by("-count")[:10])
        return Response({
            "total": self.queryset.count(),
            "by_user": by_user,
            "by_action": by_action,
            "by_resource": by_resource,
        })
