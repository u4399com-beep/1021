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

    @action(detail=False, methods=["post"], url_path="generate-drm")
    def generate_drm(self, request):
        """Generate a DRM-protected EPUB variant.

        Body: {book_id, template_id}
        Returns: {record_id, key_id, key_b64, encrypted_file_path}
        """
        from .drm import generate_drm_key, make_encrypted_epub
        from apps.sites.models import Site

        book_id = request.data.get("book_id")
        template_id = request.data.get("template_id")
        site_id = request.data.get("site_id")  # optional
        try:
            book = Book.objects.get(pk=book_id)
            template = DownloadTemplate.objects.get(pk=template_id)
        except (Book.DoesNotExist, DownloadTemplate.DoesNotExist) as e:
            return Response({"error": str(e)}, status=404)

        # 1. Generate plain EPUB first
        if template.output_format != "epub":
            return Response({"error": "DRM only supports EPUB"}, status=400)

        site = Site.objects.filter(pk=site_id).first() if site_id else None
        try:
            plain_record = build_download(book, template, user=request.user, site=site)
        except Exception as e:
            return Response({"error": repr(e)}, status=500)

        # 2. Generate DRM key
        key_bytes, key_b64 = generate_drm_key()

        # 3. Encrypt
        try:
            from pathlib import Path
            plain_path = Path(plain_record.file_path)
            encrypted_path = make_encrypted_epub(plain_path, key_bytes)
        except RuntimeError as e:
            return Response({"error": str(e)}, status=400)

        # 4. Create a second DownloadRecord for the encrypted version
        encrypted_record = DownloadRecord.objects.create(
            template=template,
            book=book,
            output_format="epub",
            file_path=str(encrypted_path),
            file_size=encrypted_path.stat().st_size,
            chapters_count=plain_record.chapters_count,
            created_by=request.user,
        )
        return Response({
            "record_id": encrypted_record.id,
            "plain_record_id": plain_record.id,
            "key_id": __import__("hashlib").sha256(key_bytes).hexdigest()[:16],
            "key_b64": key_b64,
            "encrypted_file_path": str(encrypted_path),
            "encrypted_size": encrypted_record.file_size,
        }, status=201)

    @action(detail=False, methods=["post"], url_path="decrypt-drm")
    def decrypt_drm(self, request):
        """Decrypt a DRM-protected EPUB.

        Body: {record_id, key_b64}
        Returns: {decrypted_record_id, decrypted_file_path}
        """
        from .drm import decrypt_epub
        from pathlib import Path
        import base64

        record_id = request.data.get("record_id")
        key_b64 = request.data.get("key_b64", "")
        if not record_id or not key_b64:
            return Response({"error": "record_id and key_b64 required"}, status=400)

        try:
            record = DownloadRecord.objects.get(pk=record_id)
        except DownloadRecord.DoesNotExist:
            return Response({"error": "record not found"}, status=404)

        try:
            key_bytes = base64.b64decode(key_b64)
        except Exception as e:
            return Response({"error": f"invalid key: {e!r}"}, status=400)

        try:
            encrypted_path = Path(record.file_path)
            decrypted_path = decrypt_epub(encrypted_path, key_bytes)
        except Exception as e:
            return Response({"error": repr(e)}, status=500)

        # New DownloadRecord for the decrypted version
        decrypted_record = DownloadRecord.objects.create(
            template=record.template,
            book=record.book,
            output_format="epub",
            file_path=str(decrypted_path),
            file_size=decrypted_path.stat().st_size,
            chapters_count=record.chapters_count,
            created_by=request.user,
        )
        return Response({
            "decrypted_record_id": decrypted_record.id,
            "decrypted_file_path": str(decrypted_path),
        })

    @action(detail=False, methods=["get"], url_path="drm-status")
    def drm_status(self, request):
        """Check if DRM crypto backend is available."""
        from .drm import diagnostics
        return Response(diagnostics())
