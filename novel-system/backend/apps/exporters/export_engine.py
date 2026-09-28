"""Data export (v30) — CSV/JSON export of books, chapters, tasks, etc."""

import csv
import json

from django.http import StreamingHttpResponse


class Echo:
    def write(self, value):
        return value


def _qs_to_dicts(qs, fields=None):
    for obj in qs.iterator():
        if fields:
            yield {f: getattr(obj, f) for f in fields}
        else:
            data = {}
            for f in obj._meta.concrete_fields:
                v = getattr(obj, f.name)
                if hasattr(v, "isoformat"):
                    v = v.isoformat()
                try:
                    json.dumps(v)
                except TypeError:
                    v = str(v)
                data[f.name] = v
            yield data


BOOK_FIELDS = ["id", "title", "slug", "intro", "status",
               "chapter_count", "volume_count", "word_count", "rating",
               "view_count", "is_published", "created_at", "updated_at"]


def export_books_csv(qs):
    writer = csv.DictWriter(Echo(), fieldnames=BOOK_FIELDS)
    def gen():
        yield b'\xef\xbb\xbf'  # UTF-8 BOM
        yield (",".join(BOOK_FIELDS) + "\r\n").encode("utf-8")
        for row in _qs_to_dicts(qs, fields=BOOK_FIELDS):
            safe = {}
            for k, v in row.items():
                if isinstance(v, (list, dict)):
                    safe[k] = json.dumps(v, ensure_ascii=False)
                else:
                    safe[k] = v
            line = ",".join(str(safe.get(f, "")) for f in BOOK_FIELDS)
            yield (line + "\r\n").encode("utf-8")
    resp = StreamingHttpResponse(gen(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="books.csv"'
    return resp


def export_books_json(qs):
    def gen():
        yield b"["
        first = True
        for row in _qs_to_dicts(qs, fields=BOOK_FIELDS):
            if not first:
                yield b","
            yield json.dumps(row, ensure_ascii=False, default=str).encode("utf-8")
            first = False
        yield b"]"
    resp = StreamingHttpResponse(gen(), content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="books.json"'
    return resp


TASK_FIELDS = ["id", "name", "status", "mode", "threads_min", "threads_max",
               "interval_min", "interval_max", "total_items", "processed_items",
               "success_items", "failed_items", "skipped_items",
               "priority", "retry_count", "schedule_enabled", "schedule_cron",
               "schedule_run_count", "created_at", "started_at", "finished_at"]


def export_tasks_csv(qs):
    def gen():
        yield b'\xef\xbb\xbf'
        yield (",".join(TASK_FIELDS) + "\r\n").encode("utf-8")
        for row in _qs_to_dicts(qs, fields=TASK_FIELDS):
            safe = {}
            for k, v in row.items():
                if isinstance(v, (list, dict)):
                    safe[k] = json.dumps(v, ensure_ascii=False)
                else:
                    safe[k] = v
            line = ",".join(str(safe.get(f, "")) for f in TASK_FIELDS)
            yield (line + "\r\n").encode("utf-8")
    resp = StreamingHttpResponse(gen(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="crawler_tasks.csv"'
    return resp


def export_tasks_json(qs):
    def gen():
        yield b"["
        first = True
        for row in _qs_to_dicts(qs, fields=TASK_FIELDS):
            if not first:
                yield b","
            yield json.dumps(row, ensure_ascii=False, default=str).encode("utf-8")
            first = False
        yield b"]"
    resp = StreamingHttpResponse(gen(), content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="crawler_tasks.json"'
    return resp


def export_queryset_csv(qs, fields, filename):
    def gen():
        yield b'\xef\xbb\xbf'
        yield (",".join(fields) + "\r\n").encode("utf-8")
        for row in _qs_to_dicts(qs, fields=fields):
            safe = {}
            for k, v in row.items():
                if isinstance(v, (list, dict)):
                    safe[k] = json.dumps(v, ensure_ascii=False)
                else:
                    safe[k] = v
            line = ",".join(str(safe.get(f, "")) for f in fields)
            yield (line + "\r\n").encode("utf-8")
    resp = StreamingHttpResponse(gen(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    return resp


def export_queryset_json(qs, fields, filename):
    def gen():
        yield b"["
        first = True
        for row in _qs_to_dicts(qs, fields=fields):
            if not first:
                yield b","
            yield json.dumps(row, ensure_ascii=False, default=str).encode("utf-8")
            first = False
        yield b"]"
    resp = StreamingHttpResponse(gen(), content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}.json"'
    return resp
