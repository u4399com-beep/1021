"""Obfuscator views — profile CRUD + synonym CRUD + interference CRUD + preview."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.account.permissions import CanEditSystem, CanViewSEO
from apps.sites.models import Site

from .engine import apply_obfuscation, apply_text_only
from .models import InterferenceSentence, ObfuscationProfile, Synonym
from .serializers import (
    InterferenceSentenceSerializer,
    ObfuscationProfileSerializer,
    PreviewSerializer,
    SynonymSerializer,
)


class ObfuscationProfileViewSet(viewsets.ModelViewSet):
    """Profile CRUD — one per site."""

    queryset = ObfuscationProfile.objects.all()
    serializer_class = ObfuscationProfileSerializer
    permission_classes = [IsAuthenticated, CanEditSystem]
    filterset_fields = ("site", "enabled")
    search_fields = ("site__host", "site__name")

    @action(detail=False, methods=["post"], url_path="enable-for-site")
    def enable_for_site(self, request):
        site_id = request.data.get("site_id")
        if not site_id:
            return Response({"error": "site_id required"}, status=400)
        try:
            site = Site.objects.get(pk=site_id)
        except Site.DoesNotExist:
            return Response({"error": "site not found"}, status=404)
        profile, _ = ObfuscationProfile.objects.get_or_create(site=site)
        profile.enabled = True
        profile.save(update_fields=["enabled"])
        return Response(ObfuscationProfileSerializer(profile).data)

    @action(detail=False, methods=["post"], url_path="disable-for-site")
    def disable_for_site(self, request):
        site_id = request.data.get("site_id")
        if not site_id:
            return Response({"error": "site_id required"}, status=400)
        try:
            site = Site.objects.get(pk=site_id)
        except Site.DoesNotExist:
            return Response({"error": "site not found"}, status=404)
        profile, _ = ObfuscationProfile.objects.get_or_create(site=site)
        profile.enabled = False
        profile.save(update_fields=["enabled"])
        return Response(ObfuscationProfileSerializer(profile).data)


class SynonymViewSet(viewsets.ModelViewSet):
    queryset = Synonym.objects.all()
    serializer_class = SynonymSerializer
    permission_classes = [IsAuthenticated, CanEditSystem]
    filterset_fields = ("category", "enabled")
    search_fields = ("word", "category")
    ordering = ("word",)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk_create(self, request):
        """Bulk add synonyms. Body: {items: [{word, synonyms, category}, ...]}"""
        items = request.data.get("items", [])
        created = 0
        for it in items:
            word = it.get("word", "").strip()
            syns = it.get("synonyms", [])
            cat = it.get("category", "general")
            if word and syns:
                _, c = Synonym.objects.update_or_create(
                    word=word, category=cat,
                    defaults={"synonyms": syns, "enabled": True},
                )
                created += 1 if c else 0
        return Response({"created": created, "total": Synonym.objects.count()})


class InterferenceSentenceViewSet(viewsets.ModelViewSet):
    queryset = InterferenceSentence.objects.all()
    serializer_class = InterferenceSentenceSerializer
    permission_classes = [IsAuthenticated, CanEditSystem]
    filterset_fields = ("category", "enabled")
    search_fields = ("text", "category")
    ordering = ("-weight", "id")


class PreviewViewSet(viewsets.ViewSet):
    """Preview the obfuscation result for a given text + site."""

    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        ser = PreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        text = data["text"]
        site_id = data.get("site_id")
        site = Site.objects.filter(pk=site_id).first() if site_id else None

        # Apply each layer independently so the user can see what each one does
        results = {}
        if data.get("html_structure", True):
            try:
                from .html_obfuscator import obfuscate_html
                results["html_structure"] = obfuscate_html(text)
            except Exception as e:
                results["html_structure"] = f"<error>{e!r}</error>"

        if data.get("transcode", True):
            try:
                from .transcoder import transcode_html_content
                results["transcode"] = transcode_html_content(
                    text,
                    full_width=True, homoglyph=True, zero_width=False,
                    punctuation=True, density=0.25,
                )
            except Exception as e:
                results["transcode"] = f"<error>{e!r}</error>"

        if data.get("rewrite", True):
            try:
                from .rewriter import rewrite_html_content
                results["rewrite"] = rewrite_html_content(text, site=site)
            except Exception as e:
                results["rewrite"] = f"<error>{e!r}</error>"

        # Full pipeline
        try:
            results["full"] = apply_obfuscation(text, site=site)
        except Exception as e:
            results["full"] = f"<error>{e!r}</error>"

        return Response({
            "original": text,
            "original_size": len(text.encode("utf-8")),
            "results": results,
            "sizes": {k: len(v.encode("utf-8")) if isinstance(v, str) else 0
                      for k, v in results.items()},
        })

    @action(detail=False, methods=["post"], url_path="diff")
    def diff(self, request):
        """Render the same HTML twice and return the diff — used to verify
        that each render produces unique structure."""
        from .diff_tool import render_twice

        text = request.data.get("text", "")
        site_id = request.data.get("site_id")
        site = Site.objects.filter(pk=site_id).first() if site_id else None

        if not text:
            return Response({"error": "text required"}, status=400)
        if not site:
            return Response({"error": "site_id required (must have obfuscation enabled)"}, status=400)

        result = render_twice(site, text)
        # Don't include full HTML in diff response to keep payload small
        result.pop("render1", None)
        result.pop("render2", None)
        result.pop("original", None)
        return Response(result)

    @action(detail=False, methods=["post"], url_path="visual-diff")
    def visual_diff(self, request):
        """Return an HTML table highlighting changes between two renders."""
        from .diff_tool import render_visual_diff

        text = request.data.get("text", "")
        site_id = request.data.get("site_id")
        site = Site.objects.filter(pk=site_id).first() if site_id else None

        if not text:
            return Response({"error": "text required"}, status=400)
        if not site:
            return Response({"error": "site_id required"}, status=400)

        result = render_visual_diff(site, text)
        return Response(result)
