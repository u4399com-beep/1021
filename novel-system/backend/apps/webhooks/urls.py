from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WebhookDeliveryViewSet, WebhookEndpointViewSet, WebhookEventViewSet

app_name = "webhooks"

router = DefaultRouter()
router.register("endpoints", WebhookEndpointViewSet)
router.register("deliveries", WebhookDeliveryViewSet)
router.register("events", WebhookEventViewSet, basename="webhook-events")

urlpatterns = [
    path("", include(router.urls)),
]
