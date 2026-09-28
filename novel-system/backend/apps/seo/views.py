"""SEO app views — sitemap, RSS feed, audit panel."""
from __future__ import annotations

from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.account.permissions import CanViewSEO
from apps.novel.models import Book
from apps.sites.models import Site

from .engine import run_audit, run_audit_all_sites
from .rss import render_book_chapter_rss, render_site_rss
from .sitemap import generate_for_all_sites, generate_for_site


# ------------------------------------------------------------------
# Sitemap.xml — served per host
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def sitemap_view(request, host: str | None = None):
    """Return sitemap.xml for the given host (or default site)."""
    host = host or request.get_host()
    try:
        site = Site.objects.get(host=host, is_active=True)
    except Site.DoesNotExist:
        return HttpResponse(f"<!-- no site for host {host} -->", status=404, content_type="text/plain")
    generate_for_site(site)
    # Re-read and serve
    from .sitemap import SITEMAP_DIR
    out = SITEMAP_DIR / f"{site.host}.xml"
    if not out.exists():
        return HttpResponse("<!-- sitemap not available -->", status=404)
    return HttpResponse(out.read_bytes(), content_type="application/xml; charset=utf-8")


# ------------------------------------------------------------------
# RSS — site-level + per-book
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def rss_site(request, host: str | None = None):
    host = host or request.get_host()
    try:
        site = Site.objects.get(host=host, is_active=True)
    except Site.DoesNotExist:
        return HttpResponse(f"<!-- no site for {host} -->", status=404)
    books = Book.objects.filter(is_published=True, is_deleted=False).order_by("-updated_at")[:50]
    xml = render_site_rss(site, books)
    return HttpResponse(xml, content_type="application/rss+xml; charset=utf-8")


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def rss_book(request, slug: str, host: str | None = None):
    host = host or request.get_host()
    try:
        site = Site.objects.get(host=host, is_active=True)
        book = Book.objects.get(slug=slug, is_deleted=False)
    except (Site.DoesNotExist, Book.DoesNotExist):
        return HttpResponse("<!-- not found -->", status=404)
    xml = render_book_chapter_rss(site, book)
    return HttpResponse(xml, content_type="application/rss+xml; charset=utf-8")


# ------------------------------------------------------------------
# SEO audit panel
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated, CanViewSEO])
def audit(request, site_id: int | None = None):
    """Run audit against one site or all sites."""
    if site_id:
        try:
            site = Site.objects.get(id=site_id)
        except Site.DoesNotExist:
            return Response({"error": "site not found"}, status=404)
        return Response(run_audit(site))
    return Response({"results": run_audit_all_sites()})


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanViewSEO])
def regenerate_sitemaps(request):
    """Trigger sitemap regeneration for all active sites."""
    paths = generate_for_all_sites()
    return Response({
        "ok": True,
        "count": len(paths),
        "files": [str(p) for p in paths],
    })


# ------------------------------------------------------------------
# Theme-level SEO check
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated, CanViewSEO])
def theme_check(request, theme_code: str | None = None):
    """Check SEO elements in theme HTML files.

    GET /seo/theme-check/                      → check all themes
    GET /seo/theme-check/<theme_code>/         → check one theme
    """
    from .theme_seo_check import check_all_themes, check_theme_files
    if theme_code:
        return Response(check_theme_files(theme_code))
    return Response({"results": check_all_themes()})
