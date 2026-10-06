"""封面重采 API (v294) — 通过 API 触发封面图重新获取。"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def refetch_all_covers(request):
    """触发封面图重新获取。
    
    Body: {limit: 0, force: false, delay: 1.0}
    Returns: {total, success, failed, skipped}
    """
    from .management.commands.refetch_covers import _download_cover_for_book
    from apps.novel.models import Book
    import time

    limit = int(request.data.get("limit", 0))
    force = bool(request.data.get("force", False))
    delay = float(request.data.get("delay", 1.0))

    qs = Book.objects.filter(is_deleted=False, cover_url__isnull=False).exclude(cover_url="")
    if not force:
        qs = qs.filter(cover="")
    if limit > 0:
        qs = qs[:limit]

    total = qs.count()
    success, failed, skipped = 0, 0, 0

    for book in qs.iterator():
        result = _download_cover_for_book(book)
        if result["ok"]:
            success += 1
        elif result.get("reason") == "no cover_url":
            skipped += 1
        else:
            failed += 1
        if delay > 0:
            time.sleep(delay)

    return Response({
        "total": total, "success": success,
        "failed": failed, "skipped": skipped,
    })
