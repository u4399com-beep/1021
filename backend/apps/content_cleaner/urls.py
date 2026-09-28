from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CleaningExecutionViewSet, CleaningRuleViewSet

app_name = "content_cleaner"

router = DefaultRouter()
router.register("rules", CleaningRuleViewSet)
router.register("executions", CleaningExecutionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
