"""Novel serializers — Book / Category / Chapter / Tag / Volume."""

from rest_framework import serializers

from .models import Author, Book, Category, Chapter, SuggestKeyword, Tag, Volume


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    children_count = serializers.IntegerField(source="children.count", read_only=True)

    class Meta:
        model = Category
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class ChapterListSerializer(serializers.ModelSerializer):
    volume_name = serializers.CharField(source="volume.name", read_only=True, default="")

    class Meta:
        model = Chapter
        fields = ("id", "title", "order_index", "volume", "volume_name",
                  "status", "fetched_at", "word_count", "disorder_applied")


class ChapterDetailSerializer(serializers.ModelSerializer):
    volume_name = serializers.CharField(source="volume.name", read_only=True, default="")

    class Meta:
        model = Chapter
        fields = "__all__"


class VolumeSerializer(serializers.ModelSerializer):
    chapters_count = serializers.IntegerField(source="chapters.count", read_only=True)

    class Meta:
        model = Volume
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class BookListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True, default="-")
    categories = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    cover_url_full = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            "id", "title", "slug", "author_name", "categories", "intro",
            "cover_url_full", "status", "word_count", "chapter_count", "volume_count",
            "rating", "view_count", "updated_at",
        )

    def get_cover_url_full(self, obj):
        if obj.cover:
            return obj.cover.url
        return obj.cover_url


class BookDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    volumes = VolumeSerializer(many=True, read_only=True)
    chapters = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = "__all__"

    def get_chapters(self, obj):
        # When the book has volumes, group chapters by volume
        chapters = obj.chapters.all().order_by("volume__order_index", "order_index")[:200]
        return ChapterListSerializer(chapters, many=True).data


class SuggestKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestKeyword
        fields = "__all__"
