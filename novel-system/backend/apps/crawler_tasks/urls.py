from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CrawlerTaskViewSet
from .sse import all_progress_stream, progress_stream

app_name = "crawler_tasks"

router = DefaultRouter()
router.register("", CrawlerTaskViewSet)

urlpatterns = [
    path("", include(router.urls)),
    # v35: SSE real-time progress
    path("<int:task_id>/progress-stream/", progress_stream, name="progress-stream"),
    path("progress-stream/all/", all_progress_stream, name="all-progress-stream"),
]
