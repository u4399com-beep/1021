from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuthorViewSet,
    BookViewSet,
    CategoryViewSet,
    ChapterViewSet,
    SuggestKeywordViewSet,
    TagViewSet,
)

app_name = "novel"

router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("authors", AuthorViewSet)
router.register("tags", TagViewSet)
router.register("books", BookViewSet)
router.register("chapters", ChapterViewSet, basename="chapter")
router.register("suggest-keywords", SuggestKeywordViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("books/<int:book_pk>/chapters/", include([
        # Nested chapters route
    ])),
]
