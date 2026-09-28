"""站群序列化器"""
from rest_framework import serializers

from .models import Site, Theme


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = "__all__"


class SiteSerializer(serializers.ModelSerializer):
    theme_code = serializers.CharField(source="theme.code", read_only=True)
    theme_name = serializers.CharField(source="theme.name", read_only=True)

    class Meta:
        model = Site
        fields = "__all__"


class SiteDetailSerializer(SiteSerializer):
    theme = ThemeSerializer(read_only=True)
