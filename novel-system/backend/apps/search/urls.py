from django.urls import path

from .views import (
    search_all,
    search_authors,
    search_books,
    search_chapters,
    search_suggest,
    search_tags,
)

app_name = "search"

urlpatterns = [
    path("", search_all, name="search-all"),
    path("books/", search_books, name="search-books"),
    path("authors/", search_authors, name="search-authors"),
    path("chapters/", search_chapters, name="search-chapters"),
    path("tags/", search_tags, name="search-tags"),
    path("suggest/", search_suggest, name="search-suggest"),
]
