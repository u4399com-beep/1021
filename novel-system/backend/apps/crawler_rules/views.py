"""采集规则 API。
from rest_framework.permissions import IsAuthenticated

提供规则 CRUD + 测试接口。测试接口会在请求时执行解析器，返回解析结果。
"""
from __future__ import annotations

import asyncio
import time

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from crawler_engine.fetcher import fetch_page_sync
from crawler_engine.parsers.factory import build_parser

from .models import CrawlerRule, CrawlerSource
from .serializers import CrawlerRuleSerializer, CrawlerSourceSerializer, RuleTestSerializer


class CrawlerSourceViewSet(viewsets.ModelViewSet):
    queryset = CrawlerSource.objects.all()
    serializer_class = CrawlerSourceSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ("name", "host")


class CrawlerRuleViewSet(viewsets.ModelViewSet):
    queryset = CrawlerRule.objects.select_related("source").all()
    serializer_class = CrawlerRuleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("source", "target", "enabled")
    search_fields = ("name", "notes")
    ordering = ("priority", "id")

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        rule = self.get_object()
        rule.enabled = True
        rule.save(update_fields=["enabled"])
        return Response({"status": "enabled"})

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        rule = self.get_object()
        rule.enabled = False
        rule.save(update_fields=["enabled"])
        return Response({"status": "disabled"})

    @action(detail=False, methods=["post"])
    def test(self, request):
        """测试一条规则（可以是已保存的 rule_id，也可以是临时编辑的 config）。

        请求体:
            - rule_id (可选): 已保存规则的 id
            - target: list | book | toc | chapter
            - config: 规则 JSON 配置
            - test_url (可选): 要测试的 URL
            - test_html (可选): 直接传入 HTML 字符串，跳过抓取
            - test_field (可选): 只测试某个字段
        """
        # P0-3: SSRF protection — validate test_url before fetching
        from crawler_engine.ssrf_guard import validate_url_or_raise
        
        ser = RuleTestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Load existing rule if rule_id given
        rule_id = data.get("rule_id")
        if rule_id:
            rule = CrawlerRule.objects.filter(id=rule_id).first()
            if not rule:
                return Response({"error": "rule not found"}, status=404)
            target = rule.target
            config = rule.config
        else:
            target = data["target"]
            config = data["config"]

        # Fetch or use provided HTML
        test_html = data.get("test_html", "").strip()
        test_url = data.get("test_url", "").strip()
        html = test_html
        if not html and test_url:
            # P0-3: SSRF protection — block private/metadata endpoints
            try:
                validate_url_or_raise(test_url)
            except ValueError as e:
                return Response({"error": f"SSRF blocked: {e}"}, status=403)
            try:
                html = fetch_page_sync(test_url)
            except Exception as e:
                return Response(
                    {"error": f"fetch failed: {e!r}"}, status=status.HTTP_502_BAD_GATEWAY
                )
        if not html:
            return Response({"error": "no html provided"}, status=400)

        # Parse
        try:
            parser = build_parser(config)
            result = parser.parse(target, html, base_url=test_url or "")
        except Exception as e:
            return Response({"error": f"parse failed: {e!r}", "trace": str(e)}, status=500)

        # Optional: filter to single field
        field = data.get("test_field")
        if field:
            result = {field: result.get(field)}

        # Persist test result if rule exists
        if rule_id:
            CrawlerRule.objects.filter(id=rule_id).update(
                last_test_html=html[:200_000],  # cap at 200KB
                last_test_result=result,
                last_test_at=timezone.now(),
            )

        return Response({
            "ok": True,
            "elapsed_ms": int((time.time() - _test_start_time) * 1000) if _test_start_time else 0,
            "html_size": len(html),
            "result": result,
        })
