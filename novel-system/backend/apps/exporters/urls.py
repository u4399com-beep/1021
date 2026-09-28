from django.urls import path

from .views import export_books, export_chapters, export_tasks

app_name = "exporters"

urlpatterns = [
    path("books/", export_books, name="export-books"),
    path("tasks/", export_tasks, name="export-tasks"),
    path("chapters/", export_chapters, name="export-chapters"),
]
