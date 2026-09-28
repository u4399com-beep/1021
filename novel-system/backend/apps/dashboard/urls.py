from django.urls import path

from .views import (
    books_added,
    storage_usage,
    success_rate_trend,
    summary,
    tasks_completed,
    top_books,
)
from .backup_views import backup_status, list_backups, trigger_backup
from .health import public_health, quick_health, system_health

app_name = "dashboard"

urlpatterns = [
    path("books-added/", books_added, name="books-added"),
    path("tasks-completed/", tasks_completed, name="tasks-completed"),
    path("success-rate/", success_rate_trend, name="success-rate"),
    path("top-books/", top_books, name="top-books"),
    path("storage/", storage_usage, name="storage"),
    path("summary/", summary, name="summary"),
    # v37: Backup
    path("backup/status/", backup_status, name="backup-status"),
    path("backup/trigger/", trigger_backup, name="backup-trigger"),
    path("backup/list/", list_backups, name="backup-list"),
    # v38: Health
    path("health/", system_health, name="system-health"),
    path("health/quick/", quick_health, name="quick-health"),
    path("health/public/", public_health, name="public-health"),
]
