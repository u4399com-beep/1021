"""Crawler app — engine diagnostics, suggest, tier testing, proxy pool, hyperbrowser."""

import base64
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
        disabled = p.record_success()
        return Response({
            "success_count": p.success_count, "auto_disabled": disabled,
            "success_rate": p.success_rate,
        })

    @action(detail=True, methods=["post"])
    def record_failure(self, request, pk=None):
        p = self.get_object()
        disabled = p.record_failure()
        return Response({
            "failure_count": p.failure_count, "auto_disabled": disabled,
            "success_rate": p.success_rate,
        })

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        p = self.get_object()
        p.reactivate()
        return Response({"status": "reactivated", "id": p.id})

    @action(detail=False, methods=["post"])
    def sweep_disabled(self, request):
        """Trigger an immediate check on all proxies — disables those below threshold."""
        disabled = []
        for p in self.get_queryset().filter(is_active=True, auto_disable_enabled=True):
            if p.should_auto_disable:
                p.record_failure()  # Will auto-disable based on threshold
                disabled.append({
                    "id": p.id, "name": p.name, "url": p.url,
                    "success_rate": p.success_rate,
                })
        return Response({"swept_count": len(disabled), "disabled": disabled})

    # ------------------------------------------------------------------
    # Windowed 24-hour stats (v20)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["get"])
    def hourly_stats(self, request, pk=None):
        """Return per-hour success/failure counts for the last 24h."""
        from .proxy_windowed_stats import get_hourly_stats
        p = self.get_object()
        hours = int(request.query_params.get("hours", 24))
        stats = get_hourly_stats(p.id, hours=hours)
        return Response({
            "proxy_id": p.id, "proxy_name": p.name,
            "hours": list(stats.values()),
        })

    @action(detail=True, methods=["get"])
    def best_hours(self, request, pk=None):
        """Return the N hours with highest success rate."""
        from .proxy_windowed_stats import get_best_hours
        p = self.get_object()
        hours = int(request.query_params.get("hours", 24))
        top_n = int(request.query_params.get("n", 5))
        return Response({
            "proxy_id": p.id,
            "best_hours": get_best_hours(p.id, hours=hours, top_n=top_n),
        })

    @action(detail=True, methods=["get"])
    def windowed_success_rate(self, request, pk=None):
        """Return success rate across the last N hours."""
        from .proxy_windowed_stats import get_windowed_success_rate
        p = self.get_object()
        hours = int(request.query_params.get("hours", 24))
        return Response({
            "proxy_id": p.id,
            "window_hours": hours,
            "success_rate": get_windowed_success_rate(p.id, window_hours=hours),
        })

    @action(detail=True, methods=["post"])
    def record_hourly(self, request, pk=None):
        """Record an hourly success/failure (called by fetcher on each request).

        Body: {success: bool}
        """
        from .proxy_windowed_stats import record_hourly
        p = self.get_object()
        success = bool(request.data.get("success", True))
        record_hourly(p.id, success=success)
        return Response({"status": "recorded", "proxy_id": p.id, "success": success})


# ------------------------------------------------------------------
# Region router diagnostics (v19)
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def region_status(request):
    """Return region router state + manual overrides."""
    from crawler_engine.region_router import diagnostics, pick_region_for
    diag = diagnostics()
    # Add sample resolutions for popular sites
    diag["samples"] = {
        "cunshu.la": pick_region_for("cunshu.la"),
        "example.com": pick_region_for("example.com"),
        "example.co.jp": pick_region_for("example.co.jp"),
        "example.de": pick_region_for("example.de"),
    }
    return Response(diag)


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanEditSystem])
def region_set_override(request):
    """Set a manual host → region override.

    Body: {host: "cunshu.la", region: "cn"}
    """
    from crawler_engine.region_router import set_host_override, pick_region_for
    host = request.data.get("host", "").strip()
    region = request.data.get("region", "").strip()
    if not host or not region:
        return Response({"error": "host and region required"}, status=400)
    set_host_override(host, region)
    return Response({"status": "ok", "host": host, "region": region,
                     "preview": pick_region_for(host)})


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanEditSystem])
def region_clear_override(request):
    """Clear a manual override.

    Body: {host: "cunshu.la"}
    """
    from crawler_engine.region_router import clear_host_override
    host = request.data.get("host", "").strip()
    if not host:
        return Response({"error": "host required"}, status=400)
    clear_host_override(host)
    return Response({"status": "cleared", "host": host})


# ------------------------------------------------------------------
# Captcha solver diagnostics
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def captcha_status(request):
    """Return captcha solver configuration status."""
    from crawler_engine.captcha_solver import diagnostics
    return Response(diagnostics())


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def captcha_solve(request):
    """Submit a captcha image (as base64) and return the solved text.

    Body: {image: "base64-encoded PNG/JPG bytes", prefer: "2captcha"|"ocr"}
    """
    from crawler_engine.captcha_solver import solve_captcha
    image_b64 = request.data.get("image", "")
    prefer = request.data.get("prefer", "2captcha")
    if not image_b64:
        return Response({"error": "image (base64) required"}, status=400)
    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception as e:
        return Response({"error": f"invalid base64: {e!r}"}, status=400)
    result = solve_captcha(image_bytes, prefer=prefer)
    return Response({
        "solved": result is not None,
        "text": result,
        "backend_used": prefer,
    })


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


# v319: 三层架构诊断
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def three_tier_status(request):
    from crawler_engine.three_tier_fetcher import three_tier_diagnostics
    return Response(three_tier_diagnostics())
