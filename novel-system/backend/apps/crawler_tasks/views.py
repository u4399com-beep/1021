"""采集任务 API — 包括立即执行 / 暂停 / 停止 / 调整参数 / 日志查询"""
from __future__ import annotations

from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import CrawlerTask, CrawlerTaskLog
from .serializers import CrawlerTaskDetailSerializer, CrawlerTaskLogSerializer, CrawlerTaskSerializer
from .tasks import run_crawler_task


class CrawlerTaskViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """采集任务 CRUD + 生命周期控制"""

    queryset = CrawlerTask.objects.all()
    serializer_class = CrawlerTaskSerializer
    permission_classes = []
    filterset_fields = ("status", "enabled", "mode")
    search_fields = ("name", "notes")
    ordering = ("-id",)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CrawlerTaskDetailSerializer
        return CrawlerTaskSerializer

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        """立即执行任务（提交到 Celery）"""
        task = self.get_object()
        if task.status in ("running", "queued"):
            return Response(
                {"error": "task already running"}, status=status.HTTP_409_CONFLICT
            )
        async_result = run_crawler_task.delay(task.id)
        task.celery_task_id = async_result.id
        task.status = "queued"
        task.started_at = timezone.now()
        task.save(update_fields=["celery_task_id", "status", "started_at"])
        return Response({"status": "queued", "celery_id": async_result.id})

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """暂停任务（标记位，worker 检查后退出当前批次）"""
        task = self.get_object()
        if task.status != "running":
            return Response({"error": "task not running"}, status=400)
        task.mark_paused()
        # Celery revoke (soft) — best effort
        from config import celery_app
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=False, signal="SIGUSR1")
        return Response({"status": "paused"})

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        """强制停止任务"""
        task = self.get_object()
        if task.status not in ("running", "paused", "queued"):
            return Response({"error": "task not active"}, status=400)
        from config import celery_app
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")
        task.mark_stopped()
        return Response({"status": "stopped"})

    @action(detail=True, methods=["post"])
    def update_params(self, request, pk=None):
        """运行中调整参数：threads / interval / mode"""
        task = self.get_object()
        for field in ("threads_min", "threads_max", "interval_min", "interval_max"):
            if field in request.data:
                setattr(task, field, request.data[field])
        task.save(update_fields=["threads_min", "threads_max", "interval_min", "interval_max"])
        return Response({"status": "updated", "task": CrawlerTaskSerializer(task).data})

    # ------------------------------------------------------------------
    # Schedule management (cron)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"])
    def set_schedule(self, request, pk=None):
        """启用 / 修改定时调度。

        请求体:
            enabled: bool
            cron: "0 3 * * *"  (5-segment cron, ignored if enabled=false)
            max_runs: int (0 = unlimited)
        """
        from .schedule import CronValidationError, sync_schedule

        task = self.get_object()
        enabled = bool(request.data.get("enabled", False))
        cron = (request.data.get("cron") or "").strip()
        max_runs = int(request.data.get("max_runs", 0) or 0)

        task.schedule_enabled = enabled
        task.schedule_cron = cron if enabled else task.schedule_cron
        task.schedule_max_runs = max_runs

        if enabled:
            try:
                sync_schedule(task)
            except CronValidationError as e:
                return Response({"error": str(e)}, status=400)
        else:
            from .schedule import disable_schedule
            disable_schedule(task)

        return Response({
            "status": "scheduled" if enabled else "unscheduled",
            "cron": task.schedule_cron,
            "next_run": task.schedule_next_run,
        })

    @action(detail=True, methods=["post"])
    def disable_schedule(self, request, pk=None):
        from .schedule import disable_schedule
        task = self.get_object()
        disable_schedule(task)
        return Response({"status": "disabled"})

    @action(detail=True, methods=["get"])
    def schedule_preview(self, request, pk=None):
        """预览下次 5 次运行时间。"""
        from .schedule import parse_cron_to_crontab
        task = self.get_object()
        if not task.schedule_enabled or not task.schedule_cron:
            return Response({"next_runs": []})
        try:
            cron_kwargs = parse_cron_to_crontab(task.schedule_cron)
        except Exception as e:
            return Response({"error": str(e)}, status=400)
        # Use croniter to compute next runs (lazy import)
        try:
            from croniter import croniter
            from datetime import datetime
            base = datetime.now()
            cron_expr = " ".join([
                cron_kwargs["minute"], cron_kwargs["hour"],
                cron_kwargs["day_of_month"], cron_kwargs["month_of_year"],
                cron_kwargs["day_of_week"],
            ])
            it = croniter(cron_expr, base)
            next_runs = [it.get_next(datetime).isoformat() for _ in range(5)]
            return Response({"next_runs": next_runs, "cron_expr": cron_expr})
        except ImportError:
            return Response({
                "next_runs": [],
                "note": "install `croniter` to preview next runs: pip install croniter"
            })

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        task = self.get_object()
        qs = task.logs.all().order_by("-id")[:200]
        return Response(CrawlerTaskLogSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        task = self.get_object()
        return Response({
            "status": task.status,
            "total": task.total_items,
            "processed": task.processed_items,
            "success": task.success_items,
            "failed": task.failed_items,
            "skipped": task.skipped_items,
            "elapsed": (task.finished_at or timezone.now()).timestamp() -
                       (task.started_at or task.created_at).timestamp() if task.started_at else 0,
        })
