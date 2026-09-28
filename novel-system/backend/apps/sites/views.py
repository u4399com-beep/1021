"""站群 API — 增删改查 + 主题切换 + 配置预览 + 重新生成 nginx 配置"""
from rest_framework.permissions import IsAuthenticated
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Site, Theme
from .serializers import SiteDetailSerializer, SiteSerializer, ThemeSerializer


class ThemeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Theme.objects.filter(is_active=True)
    serializer_class = ThemeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        """返回主题在某站点下的渲染预览（前端 iframe 加载）"""
        theme = self.get_object()
        return Response({
            "preview_url": f"/preview/{theme.code}/",
            "config": theme.default_config,
        })


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ("is_active", "theme")
    search_fields = ("host", "name")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SiteDetailSerializer
        return SiteSerializer

    @action(detail=True, methods=["post"])
    def regenerate_nginx(self, request, pk=None):
        """调用 management 命令重新生成 nginx 配置文件"""
        from .management.commands.generate_nginx_conf import Command
        site = self.get_object()
        cmd = Command()
        cmd.handle_site(site)  # type: ignore[attr-defined]
        return Response({"status": "ok", "host": site.host})

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        site = self.get_object()
        return Response({
            "url": f"/preview/?host={site.host}",
            "theme": site.theme.code,
            "title": site.site_title,
        })
