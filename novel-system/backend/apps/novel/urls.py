from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuthorViewSet,
    BookViewSet,
    CategoryViewSet,
    ChapterViewSet,
    SuggestKeywordViewSet,
    TagViewSet,
    VolumeViewSet,
)

app_name = "novel"

router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("authors", AuthorViewSet)
router.register("tags", TagViewSet)
router.register("books", BookViewSet)
router.register("chapters", ChapterViewSet, basename="chapter")
router.register("volumes", VolumeViewSet)
router.register("suggest-keywords", SuggestKeywordViewSet)

from .cover_refetch_api import refetch_all_covers

urlpatterns = [
    path("", include(router.urls)),
    path("refetch-covers/", refetch_all_covers, name="refetch-covers"),
    path("books/<int:book_pk>/chapters/", include([
        # Nested chapters route
    ])),
]
