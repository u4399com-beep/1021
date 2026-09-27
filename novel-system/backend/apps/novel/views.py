"""Novel API views."""
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Author, Book, Category, Chapter, SuggestKeyword, Tag, Volume
from .serializers import (
    AuthorSerializer,
    BookDetailSerializer,
    BookListSerializer,
    CategorySerializer,
    ChapterDetailSerializer,
    ChapterListSerializer,
    SuggestKeywordSerializer,
    TagSerializer,
    VolumeSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("parent",)
    search_fields = ("name",)
    ordering = ("order", "id")

    @action(detail=False, methods=["get"])
    def tree(self, request):
        qs = Category.objects.filter(is_active=True, parent__isnull=True).order_by("order")
        data = []
        for c in qs:
            d = CategorySerializer(c).data
            d["children"] = CategorySerializer(c.children.all().order_by("order"), many=True).data
            data.append(d)
        return Response(data)


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("name", "alias")


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.IsAuthenticated,)
    search_fields = ("name",)


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.filter(is_deleted=False)
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("status", "is_published", "categories", "author")
    search_fields = ("title", "intro", "tags__name")
    ordering_fields = ("created_at", "updated_at", "rating", "view_count", "word_count")

    def get_serializer_class(self):
        if self.action == "list":
            return BookListSerializer
        return BookDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        kw = self.request.query_params.get("q")
        if kw:
            qs = qs.filter(Q(title__icontains=kw) | Q(intro__icontains=kw) | Q(tags__name__icontains=kw)).distinct()
        return qs

    @action(detail=True, methods=["post"])
    def republish(self, request, pk=None):
        book = self.get_object()
        book.is_published = True
        book.save(update_fields=["is_published"])
        return Response({"status": "published"})

    @action(detail=True, methods=["delete"])
    def soft_delete(self, request, pk=None):
        book = self.get_object()
        book.is_deleted = True
        book.save(update_fields=["is_deleted"])
        return Response({"status": "deleted"})

    @action(detail=True, methods=["get"])
    def disorder_check(self, request, pk=None):
        """Check the disorder reordering for this book — see _check_disorder."""
        from crawler_engine.pipeline import _check_disorder
        book = self.get_object()
        result = _check_disorder(book)
        return Response(result)


class ChapterViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("book", "status", "volume")
    ordering_fields = ("order_index", "fetched_at", "updated_at")
    ordering = ("order_index",)

    def get_queryset(self):
        return Chapter.objects.filter(book_id=self.kwargs.get("book_pk")).order_by("order_index") \
            if "book_pk" in self.kwargs else Chapter.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ChapterListSerializer
        return ChapterDetailSerializer


class VolumeViewSet(viewsets.ModelViewSet):
    """Volume CRUD — managed per book."""

    queryset = Volume.objects.all()
    serializer_class = VolumeSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("book",)
    ordering = ("order_index", "id")

    @action(detail=True, methods=["post"])
    def assign_chapters(self, request, pk=None):
        """批量分配章节到本分卷。

        Body: {chapter_ids: [12, 13, 14]}
        """
        vol = self.get_object()
        ids = request.data.get("chapter_ids", [])
        updated = Chapter.objects.filter(book_id=vol.book_id, id__in=ids).update(volume=vol)
        vol.update_chapter_count()
        vol.book.update_volume_count()
        return Response({"updated": updated, "volume_chapters_count": vol.chapter_count})

    @action(detail=True, methods=["post"])
    def auto_split_by_count(self, request, pk=None):
        """Auto-split the book's chapters into N volumes of equal size.

        Body: {count: 3, prefix: "第{}卷"}
        """
        import math
        vol = self.get_object()
        book = vol.book
        count = int(request.data.get("count", 3))
        prefix = request.data.get("prefix", "第{}卷")
        chapters = list(book.chapters.all().order_by("order_index"))
        if not chapters:
            return Response({"error": "no chapters"}, status=400)
        chunk_size = math.ceil(len(chapters) / count)
        created_vols = []
        for i in range(count):
            start = i * chunk_size
            end = start + chunk_size
            chunk = chapters[start:end]
            vol_name = prefix.format(i + 1) if "{}" in prefix else f"{prefix}{i + 1}"
            new_vol, _ = Volume.objects.update_or_create(
                book=book, order_index=i + 1,
                defaults={"name": vol_name},
            )
            Chapter.objects.filter(id__in=[c.id for c in chunk]).update(volume=new_vol)
            new_vol.update_chapter_count()
            created_vols.append(VolumeSerializer(new_vol).data)
        book.update_volume_count()
        return Response({"volumes": created_vols, "count": len(created_vols)})


class SuggestKeywordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SuggestKeyword.objects.all()
    serializer_class = SuggestKeywordSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("main_book", "source")
    search_fields = ("keyword",)
