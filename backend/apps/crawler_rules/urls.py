from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CrawlerRuleViewSet, CrawlerSourceViewSet

app_name = "crawler_rules"

router = DefaultRouter()
router.register("sources", CrawlerSourceViewSet)
router.register("", CrawlerRuleViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
