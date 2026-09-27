"""Crawler app — engine diagnostics, suggest, tier testing, proxy pool, hyperbrowser."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.account.permissions import CanEditSystem
from crawler_engine.anti_detection.pool import (
    get_hyperbrowser_session,
    hyperbrowser_diagnostics,
    list_hyperbrowser_sessions,
    release_hyperbrowser_session,
)
from crawler_engine.fetcher import diagnose, test_url
from crawler_engine.utils.suggest import fetch_all

from .models import ProxyPool
from .serializers import ProxyPoolSerializer


# ------------------------------------------------------------------
# Engine diagnostics + per-tier test
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def engine_status(request):
    """Report which crawler tiers are installed and configured."""
    return Response({"tiers": diagnose()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def engine_test(request):
    url = request.data.get("url", "").strip()
    tier = request.data.get("tier")
    if not url:
        return Response({"error": "url required"}, status=400)
    try:
        result = test_url(url, tier=tier)
        return Response(result)
    except Exception as e:
        return Response({"error": repr(e)}, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def engine_fetch(request):
    """Full fallback fetch — walk tiers in order, return the first HTML."""
    from crawler_engine.fetcher import fetch_page
    url = request.data.get("url", "").strip()
    if not url:
        return Response({"error": "url required"}, status=400)
    try:
        html = fetch_page(url, use_browser=bool(request.data.get("use_browser", False)))
        return Response({
            "url": url, "html_size": len(html), "preview": html[:2000],
        })
    except Exception as e:
        return Response({"error": repr(e)}, status=502)


# ------------------------------------------------------------------
# Hyperbrowser session management
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def hyperbrowser_status(request):
    """Return active Hyperbrowser sessions + config status."""
    return Response(hyperbrowser_diagnostics())


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanEditSystem])
def hyperbrowser_create_session(request):
    """Manually create a new Hyperbrowser session and return its CDP URL."""
    try:
        sess = get_hyperbrowser_session()
        return Response(sess)
    except RuntimeError as e:
        return Response({"error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanEditSystem])
def hyperbrowser_release_session(request):
    """Release a Hyperbrowser session by id."""
    sid = request.data.get("session_id", "")
    if not sid:
        return Response({"error": "session_id required"}, status=400)
    release_hyperbrowser_session(sid)
    return Response({"status": "released", "session_id": sid})


# ------------------------------------------------------------------
# Proxy pool CRUD
# ------------------------------------------------------------------
class ProxyPoolViewSet(viewsets.ModelViewSet):
    queryset = ProxyPool.objects.all()
    serializer_class = ProxyPoolSerializer
    permission_classes = [IsAuthenticated, CanEditSystem]
    filterset_fields = ("is_active", "proxy_type", "region")
    search_fields = ("name", "url", "region", "notes")
    ordering = ("-priority", "id")

    @action(detail=False, methods=["post"])
    def check_all(self, request):
        """Quick-check all active proxies with a HEAD request."""
        import httpx
        from django.utils import timezone
        from datetime import timedelta

        results = []
        test_url = request.data.get("test_url") or "https://www.example.com/"
        for p in self.get_queryset().filter(is_active=True):
            ok = False
            try:
                with httpx.Client(proxy=p.url, timeout=10) as cli:
                    r = cli.head(test_url)
                    ok = r.status_code < 500
            except Exception:
                ok = False
            p.last_check_at = timezone.now()
            p.last_check_ok = ok
            p.save(update_fields=["last_check_at", "last_check_ok"])
            results.append({
                "id": p.id, "name": p.name, "url": p.url, "ok": ok,
            })
        return Response({"results": results})

    @action(detail=True, methods=["post"])
    def record_success(self, request, pk=None):
        p = self.get_object()
        p.success_count += 1
        p.save(update_fields=["success_count"])
        return Response({"success_count": p.success_count})

    @action(detail=True, methods=["post"])
    def record_failure(self, request, pk=None):
        p = self.get_object()
        p.failure_count += 1
        p.save(update_fields=["failure_count"])
        return Response({"failure_count": p.failure_count})


# ------------------------------------------------------------------
# Search engine suggestion
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([AllowAny])
def suggest(request):
    kw = request.query_params.get("kw", "")
    if not kw:
        return Response({"error": "missing kw"}, status=400)
    providers = (request.query_params.get("providers") or "baidu,bing,google,sogou").split(",")
    result = fetch_all(kw, providers)
    return Response({"keyword": kw, "suggestions": result})
