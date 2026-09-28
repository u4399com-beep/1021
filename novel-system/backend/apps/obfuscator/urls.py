from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InterferenceSentenceViewSet,
    ObfuscationProfileViewSet,
    PreviewViewSet,
    SynonymViewSet,
)

app_name = "obfuscator"

router = DefaultRouter()
router.register("profiles", ObfuscationProfileViewSet)
router.register("synonyms", SynonymViewSet)
router.register("interferences", InterferenceSentenceViewSet)
router.register("preview", PreviewViewSet, basename="preview")

urlpatterns = [
    path("", include(router.urls)),
]
