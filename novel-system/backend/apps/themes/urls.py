from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ThemeViewSet

app_name = "themes"

router = DefaultRouter()
router.register("", ThemeViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
