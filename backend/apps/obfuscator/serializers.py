"""Obfuscator serializers."""
from rest_framework import serializers

from .models import InterferenceSentence, ObfuscationProfile, Synonym


class ObfuscationProfileSerializer(serializers.ModelSerializer):
    site_host = serializers.CharField(source="site.host", read_only=True)

    class Meta:
        model = ObfuscationProfile
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class SynonymSerializer(serializers.ModelSerializer):
    class Meta:
        model = Synonym
        fields = "__all__"
        read_only_fields = ("created_at",)


class InterferenceSentenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterferenceSentence
        fields = "__all__"
        read_only_fields = ("created_at", "used_count")


class PreviewSerializer(serializers.Serializer):
    """Request / response for preview endpoints."""
    text = serializers.CharField(required=True)
    site_id = serializers.IntegerField(required=False)
    # Optional layer toggles
    html_structure = serializers.BooleanField(required=False, default=True)
    transcode = serializers.BooleanField(required=False, default=True)
    rewrite = serializers.BooleanField(required=False, default=True)
