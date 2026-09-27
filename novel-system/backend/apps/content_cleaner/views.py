"""清洗 API — 规则 CRUD + 试清洗"""
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .engine import clean_content
from .models import CleaningExecution, CleaningRule


class CleaningRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CleaningRule
        fields = "__all__"


class CleaningRuleViewSet(viewsets.ModelViewSet):
    queryset = CleaningRule.objects.all()
    serializer_class = CleaningRuleSerializer
    permission_classes = []
    filterset_fields = ("target", "strategy", "enabled")
    ordering = ("priority", "id")

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """传入 HTML + target，返回清洗后的结果"""
        html = request.data.get("html", "")
        target = request.data.get("target", "chapter")
        cleaned = clean_content(html, target=target)
        return Response({
            "before_size": len(html),
            "after_size": len(cleaned),
            "cleaned": cleaned,
        })


class CleaningExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CleaningExecution
        fields = "__all__"


class CleaningExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CleaningExecution.objects.all()
    serializer_class = CleaningExecutionSerializer
    permission_classes = []
    filterset_fields = ("rule", "target_type")
    ordering = ("-executed_at",)
