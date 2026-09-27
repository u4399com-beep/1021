"""Theme API — list themes, preview, get theme metadata."""
from __future__ import annotations

from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.sites.models import Theme
from apps.sites.serializers import ThemeSerializer

from .engine import THEME_TEMPLATES, get_theme_path


class ThemeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Theme.objects.filter(is_active=True)
    serializer_class = ThemeSerializer
    permission_classes = []

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
