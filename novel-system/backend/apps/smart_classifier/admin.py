from django.contrib import admin

from .models import CategoryKeyword, FinishedPattern


@admin.register(CategoryKeyword)
class CategoryKeywordAdmin(admin.ModelAdmin):
    list_display = ("category_name", "keyword", "weight")
    list_filter = ("category_name",)
    search_fields = ("keyword",)
    ordering = ("category_name", "keyword")


@admin.register(FinishedPattern)
class FinishedPatternAdmin(admin.ModelAdmin):
    list_display = ("name", "pattern", "priority", "enabled")
    list_filter = ("enabled",)
    search_fields = ("name", "pattern")
