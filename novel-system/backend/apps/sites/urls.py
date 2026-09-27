from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SiteViewSet, ThemeViewSet

app_name = "sites"

router = DefaultRouter()
router.register("themes", ThemeViewSet)
router.register("", SiteViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
