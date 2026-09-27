"""下载 API — 模板 CRUD + 触发下载"""
from __future__ import annotations

from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.novel.models import Book

from .engine import build_download
from .models import DownloadRecord, DownloadTemplate
from .serializers import DownloadRecordSerializer, DownloadTemplateSerializer


class DownloadTemplateViewSet(viewsets.ModelViewSet):
    queryset = DownloadTemplate.objects.all()
    serializer_class = DownloadTemplateSerializer
    permission_classes = []
    filterset_fields = ("output_format", "enabled")
    search_fields = ("name",)


class DownloadRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DownloadRecord.objects.all()
    serializer_class = DownloadRecordSerializer
    permission_classes = []
    filterset_fields = ("template", "book", "created_by")
    ordering = ("-id",)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        rec = self.get_object()
        import os
        if not os.path.isfile(rec.file_path):
            raise Http404
        return FileResponse(open(rec.file_path, "rb"), as_attachment=True, filename=os.path.basename(rec.file_path))


class GenerateDownloadViewSet(viewsets.ViewSet):
    """触发下载生成"""

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        book_id = request.data.get("book_id")
        template_id = request.data.get("template_id")
        try:
            book = Book.objects.get(pk=book_id)
            template = DownloadTemplate.objects.get(pk=template_id)
        except (Book.DoesNotExist, DownloadTemplate.DoesNotExist) as e:
            return Response({"error": str(e)}, status=404)

        # Run synchronously — for large books, offload to Celery
        try:
            record = build_download(book, template, user=request.user)
        except Exception as e:
            return Response({"error": repr(e)}, status=500)
        return Response(DownloadRecordSerializer(record).data, status=201)
