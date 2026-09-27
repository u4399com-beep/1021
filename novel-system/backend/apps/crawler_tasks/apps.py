from django.apps import AppConfig


class CrawlerTasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crawler_tasks"
    verbose_name = "采集任务"
