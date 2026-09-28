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

# v42-v52 extra endpoints
from .extra_views import (
    archive_chapters, audit_chapter_content, clear_slow_queries,
    dispatch_alerts, fill_covers, generate_report,
    smart_schedule, slow_queries, source_health,
)

urlpatterns += [
    path("alerts/dispatch/", dispatch_alerts, name="dispatch-alerts"),
    path("archive/chapters/", archive_chapters, name="archive-chapters"),
    path("source-health/", source_health, name="source-health"),
    path("audit-chapter/", audit_chapter_content, name="audit-chapter"),
    path("fill-covers/", fill_covers, name="fill-covers"),
    path("generate-report/", generate_report, name="generate-report"),
    path("smart-schedule/", smart_schedule, name="smart-schedule"),
    path("slow-queries/", slow_queries, name="slow-queries"),
    path("slow-queries/clear/", clear_slow_queries, name="clear-slow-queries"),
]
