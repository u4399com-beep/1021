from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .engine import classify_book, detect_finished
from .models import CategoryKeyword, FinishedPattern


class CategoryKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryKeyword
        fields = "__all__"


class FinishedPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinishedPattern
        fields = "__all__"


class CategoryKeywordViewSet(viewsets.ModelViewSet):
    queryset = CategoryKeyword.objects.all()
    serializer_class = CategoryKeywordSerializer
    permission_classes = []
    filterset_fields = ("category_name",)
    search_fields = ("keyword",)


class FinishedPatternViewSet(viewsets.ModelViewSet):
    queryset = FinishedPattern.objects.all()
    serializer_class = FinishedPatternSerializer
    permission_classes = []


class ClassifyTestViewSet(viewsets.ViewSet):
    """试分类 + 试完结判断"""

    @action(detail=False, methods=["post"], url_path="classify")
    def classify(self, request):
        title = request.data.get("title", "")
        intro = request.data.get("intro", "")
        snippet = request.data.get("snippet", "")
        top_n = int(request.data.get("top_n", 3))
        result = classify_book(title, intro, snippet, top_n=top_n)
        return Response({"categories": result})

    @action(detail=False, methods=["post"], url_path="finished")
    def finished(self, request):
        title = request.data.get("title", "")
        intro = request.data.get("intro", "")
        last_chapter = request.data.get("last_chapter_title", "")
        result = detect_finished(title, intro, last_chapter)
        return Response({"finished": result})
