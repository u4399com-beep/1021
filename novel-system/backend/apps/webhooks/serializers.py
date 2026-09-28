"""Webhook serializers."""
from rest_framework import serializers

from .models import WebhookDelivery, WebhookEndpoint


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = "__all__"
        read_only_fields = ("sent_count", "fail_count", "last_sent_at", "last_error")


class WebhookDeliverySerializer(serializers.ModelSerializer):
    endpoint_name = serializers.CharField(source="endpoint.name", read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = "__all__"
