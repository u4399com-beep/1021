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

# v54-v67 endpoints
from .v54_endpoints import (
    auto_adjust_priorities, cache_diagnostics, check_duplicates,
    detect_updates, domain_rate, db_pool_diagnostics, export_rules,
    import_rules, integrity_check, merge_duplicates, predict_eta,
    repair_counts, rollback_rule, save_rule_version, score_chapter_content,
    segment_content, traffic_summary,
)

urlpatterns += [
    path("dedup/check/", check_duplicates, name="check-duplicates"),
    path("dedup/merge/", merge_duplicates, name="merge-duplicates"),
    path("domain-rate/", domain_rate, name="domain-rate"),
    path("quality/score/", score_chapter_content, name="score-chapter"),
    path("rules/save-version/", save_rule_version, name="save-rule-version"),
    path("rules/rollback/", rollback_rule, name="rollback-rule"),
    path("tasks/eta/", predict_eta, name="predict-eta"),
    path("db-pool/", db_pool_diagnostics, name="db-pool"),
    path("cache/diagnostics/", cache_diagnostics, name="cache-diag"),
    path("content/segment/", segment_content, name="segment-content"),
    path("rules/export/", export_rules, name="export-rules"),
    path("rules/import/", import_rules, name="import-rules"),
    path("traffic/", traffic_summary, name="traffic-summary"),
    path("auto-priority/", auto_adjust_priorities, name="auto-priority"),
    path("detect-updates/", detect_updates, name="detect-updates"),
    path("integrity/", integrity_check, name="integrity-check"),
    path("integrity/repair/", repair_counts, name="repair-counts"),
]

# v69-v82 endpoints
from .v69_endpoints import (
    ad_slots_for_page, ai_generate_book_rule, ai_generate_chapter_rule,
    ai_generate_list_rule, cluster_status, create_payment_order,
    extract_tags, import_books, rate_book, reader_profile, reader_register,
    recent_notifications, reading_themes, rule_presets, run_benchmark,
)
from .v54_endpoints import *  # keep v54-v67 imports working

urlpatterns += [
    # v69
    path("ai/generate-list-rule/", ai_generate_list_rule, name="ai-list-rule"),
    path("ai/generate-book-rule/", ai_generate_book_rule, name="ai-book-rule"),
    path("ai/generate-chapter-rule/", ai_generate_chapter_rule, name="ai-chapter-rule"),
    # v70
    path("ads/for-page/", ad_slots_for_page, name="ads-for-page"),
    # v71-v72
    path("reader/register/", reader_register, name="reader-register"),
    path("reader/<int:reader_id>/", reader_profile, name="reader-profile"),
    path("payment/create-order/", create_payment_order, name="create-payment-order"),
    # v74
    path("cluster/status/", cluster_status, name="cluster-status"),
    # v75
    path("import/books/", import_books, name="import-books"),
    # v76
    path("notifications/recent/", recent_notifications, name="recent-notifications"),
    # v77
    path("rule-presets/", rule_presets, name="rule-presets"),
    # v78
    path("reading-themes/", reading_themes, name="reading-themes"),
    # v80
    path("rate-book/", rate_book, name="rate-book"),
    # v81
    path("extract-tags/", extract_tags, name="extract-tags"),
    # v82
    path("benchmark/", run_benchmark, name="run-benchmark"),
]
