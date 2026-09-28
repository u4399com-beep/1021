"""Public API endpoints — dashboard stats, settings overview."""

from django.db.models import Count, Sum
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.crawler_tasks.models import CrawlerTask
from apps.novel.models import Book, Chapter
from apps.sites.models import Site


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def dashboard(request):
    """Dashboard overview stats."""
    return Response({
        "books": Book.objects.filter(is_deleted=False).count(),
        "chapters": Chapter.objects.count(),
        "tasks": CrawlerTask.objects.count(),
        "running_tasks": CrawlerTask.objects.filter(status="running").count(),
        "sites": Site.objects.count(),
        "by_status": list(Book.objects.values("status").annotate(count=Count("id"))),
        "by_source": list(
            Book.objects.exclude(source_site="").values("source_site").annotate(count=Count("id")).order_by("-count")[:10]
        ),
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def system_info(request):
    """System info — version, queue length, disk usage."""
    import sys
    import django
    from django.core.cache import cache
    return Response({
        "django": django.get_version(),
        "python": sys.version.split()[0],
        "queue_len": cache.get("crawler_queue_len", 0) or 0,
    })
