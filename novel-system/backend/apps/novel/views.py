"""Novel API views."""
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Author, Book, Category, Chapter, SuggestKeyword, Tag
from .serializers import (
    AuthorSerializer,
    BookDetailSerializer,
    BookListSerializer,
    CategorySerializer,
    ChapterDetailSerializer,
    ChapterListSerializer,
    SuggestKeywordSerializer,
    TagSerializer,
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


class ChapterViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("book", "status")
    ordering_fields = ("order_index", "fetched_at", "updated_at")
    ordering = ("order_index",)

    def get_queryset(self):
        return Chapter.objects.filter(book_id=self.kwargs.get("book_pk")).order_by("order_index") \
            if "book_pk" in self.kwargs else Chapter.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ChapterListSerializer
        return ChapterDetailSerializer


class SuggestKeywordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SuggestKeyword.objects.all()
    serializer_class = SuggestKeywordSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ("main_book", "source")
    search_fields = ("keyword",)
