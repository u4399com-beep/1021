"""Theme API — list themes, preview, get theme metadata."""

from pathlib import Path

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FileUploadParser, FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.sites.models import Theme
from apps.sites.serializers import ThemeSerializer

from .engine import THEME_TEMPLATES, get_theme_path


class ThemeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Theme.objects.filter(is_active=True)
    serializer_class = ThemeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def files(self, request, pk=None):
        theme = self.get_object()
        code = theme.code
        info = THEME_TEMPLATES.get(code, {})
        return Response({
            "code": code,
            "name": theme.name,
            "files": info.get("files", []),
            "static_dir": info.get("static_dir", ""),
            "exists_on_disk": get_theme_path(code).exists(),
        })

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        from .engine import render_theme_page
        theme = self.get_object()
        page = request.data.get("page", "index")
        context = request.data.get("context", {})
        html = render_theme_page(theme.code, page, context)
        return Response({"html": html})

    # ─── v24: Plugin system ───────────────────────────────────
    @action(detail=False, methods=["get"], url_path="list-on-disk")
    def list_on_disk(self, request):
        """List all themes (built-in + custom) on disk."""
        from .plugin_system import list_themes_on_disk
        return Response({"themes": list_themes_on_disk()})

    @action(detail=False, methods=["post"], url_path="upload",
            parser_classes=[MultiPartParser, FormParser, FileUploadParser])
    def upload(self, request):
        """Upload a theme as a ZIP file.

        POST form-data:
          - file: theme.zip
          - overwrite: bool (optional, default false)

        Returns: {ok, theme_id, code, errors}
        """
        from .plugin_system import install_theme_zip
        f = request.FILES.get("file") or request.FILES.get("zip")
        overwrite = str(request.data.get("overwrite", "false")).lower() in ("true", "1", "yes")
        if not f:
            return Response({"error": "file required (upload as 'file' or 'zip')"}, status=400)

        # Save uploaded zip to a temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            for chunk in f.chunks():
                tmp.write(chunk)
            tmp_path = Path(tmp.name)
        try:
            result = install_theme_zip(tmp_path, overwrite=overwrite)
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass
        if not result["ok"]:
            return Response(result, status=400)
        return Response(result, status=201)

    @action(detail=True, methods=["delete"], url_path="delete-custom")
    def delete_custom(self, request, pk=None):
        """Delete a custom theme. Cannot delete built-in themes."""
        from .plugin_system import delete_custom_theme
        theme = self.get_object()
        result = delete_custom_theme(theme.code)
        if not result["ok"]:
            return Response(result, status=400)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="sample-template")
    def sample_template(self, request):
        """Generate a sample theme ZIP for users to download as a starting template."""
        from django.http import HttpResponse
        import tempfile
        from .plugin_system import create_sample_theme_zip
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            create_sample_theme_zip(tmp_path)
            content = tmp_path.read_bytes()
            resp = HttpResponse(
                content,
                content_type="application/zip",
                headers={"Content-Disposition": 'attachment; filename="sample-theme.zip"'},
            )
            return resp
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass
