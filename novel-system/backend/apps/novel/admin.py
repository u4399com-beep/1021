from django.contrib import admin

from .models import Author, Book, Category, Chapter, SuggestKeyword, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "alias", "books_count", "created_at")
    search_fields = ("name", "alias")

    def books_count(self, obj):
        return obj.books.count()


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title", "author", "status", "chapter_count", "word_count",
        "rating", "is_published", "updated_at",
    )
    list_filter = ("status", "is_published", "categories", "is_deleted")
    search_fields = ("title", "intro", "author__name")
    raw_id_fields = ("author",)
    filter_horizontal = ("categories", "tags")
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_published", "mark_unpublished"]

    def mark_published(self, request, qs):
        qs.update(is_published=True)
    mark_published.short_description = "发布选中书籍"

    def mark_unpublished(self, request, qs):
        qs.update(is_published=False)
    mark_unpublished.short_description = "下架选中书籍"


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("book", "order_index", "title", "status", "word_count", "fetched_at")
    list_filter = ("status",)
    search_fields = ("title", "content")
    raw_id_fields = ("book",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "is_auto", "suggest_source")
    list_filter = ("is_auto",)


@admin.register(SuggestKeyword)
class SuggestKeywordAdmin(admin.ModelAdmin):
    list_display = ("keyword", "source", "main_book", "weight")
    list_filter = ("source",)
