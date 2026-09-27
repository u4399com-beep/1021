"""Crawler app — engine diagnostics, suggest, tier testing."""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from crawler_engine.fetcher import diagnose, test_url
from crawler_engine.utils.suggest import fetch_all


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
    """Test-fetch a URL with a specific tier or all tiers in fallback order.

    POST body:
        url: https://example.com/list
        tier: httpx | firecrawl | browser-use | playwright   (optional)
    """
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
    """Full fallback fetch — walk tiers in order, return the first HTML.

    Use this to validate the entire pipeline.
    """
    from crawler_engine.fetcher import fetch_page
    url = request.data.get("url", "").strip()
    if not url:
        return Response({"error": "url required"}, status=400)
    try:
        html = fetch_page(url, use_browser=bool(request.data.get("use_browser", False)))
        return Response({
            "url": url,
            "html_size": len(html),
            "preview": html[:2000],
        })
    except Exception as e:
        return Response({"error": repr(e)}, status=502)


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
