from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CrawlerTaskViewSet

app_name = "crawler_tasks"

router = DefaultRouter()
router.register("", CrawlerTaskViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
