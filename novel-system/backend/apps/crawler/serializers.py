"""Crawler serializers — ProxyPool + Hyperbrowser diagnostics."""
from rest_framework import serializers

from .models import ProxyPool


class ProxyPoolSerializer(serializers.ModelSerializer):
    success_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = ProxyPool
        fields = "__all__"
        read_only_fields = ("success_count", "failure_count", "last_used_at", "last_check_at", "last_check_ok")
