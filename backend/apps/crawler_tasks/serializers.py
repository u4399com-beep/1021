"""采集任务序列化器"""
from rest_framework import serializers

from apps.crawler_rules.serializers import CrawlerRuleSerializer
from .models import CrawlerTask, CrawlerTaskLog


class CrawlerTaskLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlerTaskLog
        fields = "__all__"


class CrawlerTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlerTask
        fields = "__all__"
        read_only_fields = (
            "status", "celery_task_id", "total_items", "processed_items",
            "success_items", "failed_items", "skipped_items",
            "started_at", "finished_at", "last_error",
            "schedule_next_run", "schedule_last_run", "schedule_run_count",
        )


class CrawlerTaskDetailSerializer(CrawlerTaskSerializer):
    """Detail serializer — extends base with nested rule serializers + logs.

    Note: parent uses `fields = "__all__"`; we keep the same `__all__`
    behavior by reusing parent's Meta and just adding the extra read-only fields.
    """
    list_rule = CrawlerRuleSerializer(read_only=True)
    book_rule = CrawlerRuleSerializer(read_only=True)
    toc_rule = CrawlerRuleSerializer(read_only=True)
    chapter_rule = CrawlerRuleSerializer(read_only=True)
    logs = serializers.SerializerMethodField()

    class Meta(CrawlerTaskSerializer.Meta):
        # `__all__` already includes all model fields; extra declared fields
        # (list_rule, book_rule, etc.) are picked up by DRF automatically.
        pass

    def get_logs(self, obj):
        qs = obj.logs.all()[:50]
        return CrawlerTaskLogSerializer(qs, many=True).data
