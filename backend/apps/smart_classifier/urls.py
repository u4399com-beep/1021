from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryKeywordViewSet,
    ClassifyTestViewSet,
    FinishedPatternViewSet,
)

app_name = "smart_classifier"

router = DefaultRouter()
router.register("category-keywords", CategoryKeywordViewSet)
router.register("finished-patterns", FinishedPatternViewSet)
router.register("test", ClassifyTestViewSet, basename="classify-test")

urlpatterns = [
    path("", include(router.urls)),
]
