"""采集规则序列化器"""
from rest_framework import serializers

from .models import CrawlerRule, CrawlerSource


class CrawlerSourceSerializer(serializers.ModelSerializer):
    rules_count = serializers.IntegerField(source="rules.count", read_only=True)

    class Meta:
        model = CrawlerSource
        fields = "__all__"


class CrawlerRuleSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True, default="-")

    class Meta:
        model = CrawlerRule
        fields = "__all__"
        read_only_fields = ("last_test_html", "last_test_result", "last_test_at")


class RuleTestSerializer(serializers.Serializer):
    """测试规则用的请求/响应序列化器"""

    rule_id = serializers.IntegerField(required=False)
    target = serializers.CharField()
    config = serializers.JSONField()
    test_url = serializers.URLField(required=False)
    test_html = serializers.CharField(required=False, allow_blank=True)
    test_field = serializers.CharField(required=False, help_text="只测试某一字段，例如 book_title")
