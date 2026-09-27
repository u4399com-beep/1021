from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DownloadRecordViewSet,
    DownloadTemplateViewSet,
    GenerateDownloadViewSet,
)

app_name = "file_download"

router = DefaultRouter()
router.register("templates", DownloadTemplateViewSet)
router.register("records", DownloadRecordViewSet)
router.register("generate", GenerateDownloadViewSet, basename="generate")

urlpatterns = [
    path("", include(router.urls)),
]
