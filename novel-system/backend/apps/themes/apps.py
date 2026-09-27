"""Themes app — registers the 5 available theme templates and provides
a renderer stub used by the multi-site front-end.
"""
from django.apps import AppConfig


class ThemesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.themes"
    verbose_name = "主题模板"
