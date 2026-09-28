from django.contrib import admin

from .models import InterferenceSentence, ObfuscationProfile, RewriteRecord, Synonym


@admin.register(ObfuscationProfile)
class ObfuscationProfileAdmin(admin.ModelAdmin):
    list_display = ("site", "enabled", "html_class_randomize", "transcode_full_width",
                    "rewrite_synonym", "seed_per_request", "updated_at")
    list_filter = ("enabled", "html_class_randomize", "transcode_full_width",
                   "rewrite_synonym", "seed_per_request")
    search_fields = ("site__host", "site__name")


@admin.register(Synonym)
class SynonymAdmin(admin.ModelAdmin):
    list_display = ("word", "category", "enabled", "synonyms_preview")
    list_filter = ("category", "enabled")
    search_fields = ("word", "synonyms")

    def synonyms_preview(self, obj):
        s = obj.synonyms or []
        return ", ".join(s[:3]) + ("..." if len(s) > 3 else "")


@admin.register(InterferenceSentence)
class InterferenceSentenceAdmin(admin.ModelAdmin):
    list_display = ("text_preview", "category", "weight", "enabled", "used_count")
    list_filter = ("category", "enabled")
    search_fields = ("text",)
    ordering = ("-weight", "id")

    def text_preview(self, obj):
        return obj.text[:60]


@admin.register(RewriteRecord)
class RewriteRecordAdmin(admin.ModelAdmin):
    list_display = ("original_hash_preview", "rewritten_hash_preview", "site", "book", "chapter", "created_at")
    list_filter = ("site", "created_at")
    search_fields = ("original_hash", "rewritten_hash")
    readonly_fields = ("original_hash", "rewritten_hash", "transformations", "site", "book", "chapter", "created_at")

    def original_hash_preview(self, obj): return obj.original_hash[:12] + "..."
    def rewritten_hash_preview(self, obj): return obj.rewritten_hash[:12] + "..."
