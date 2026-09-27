"""Crawler app — high-level views (job history, run book search suggest)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from crawler_engine.utils.suggest import fetch_all


@api_view(["GET"])
@permission_classes([AllowAny])
def suggest(request):
    """Search engine suggestions — baidu / bing / google / sogou autocomplete."""
    kw = request.query_params.get("kw", "")
    if not kw:
        return Response({"error": "missing kw"}, status=400)
    providers = (request.query_params.get("providers") or "baidu,bing,google,sogou").split(",")
    result = fetch_all(kw, providers)
    return Response({"keyword": kw, "suggestions": result})
