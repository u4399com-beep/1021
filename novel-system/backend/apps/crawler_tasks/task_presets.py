"""Task preset library (v86) — common task configurations."""
from __future__ import annotations

TASK_PRESETS = {
    "full_crawl": {
        "name": "全量采集", "mode": "full", "threads_min": 2, "threads_max": 5,
        "interval_min": 1.0, "interval_max": 3.0, "content_storage": "db",
        "enable_cleaner": True, "enable_classifier": True,
    },
    "incremental_update": {
        "name": "增量更新", "mode": "incremental", "threads_min": 1, "threads_max": 3,
        "interval_min": 2.0, "interval_max": 5.0, "content_storage": "db",
        "enable_cleaner": True, "enable_dedup_by_url": True,
    },
    "fast_scan": {
        "name": "快速扫描", "mode": "incremental", "threads_min": 5, "threads_max": 10,
        "interval_min": 0.5, "interval_max": 1.5, "content_storage": "db",
        "enable_cleaner": False, "enable_classifier": False,
    },
    "txt_export": {
        "name": "TXT导出", "mode": "full", "threads_min": 2, "threads_max": 4,
        "interval_min": 1.0, "interval_max": 2.0, "content_storage": "txt",
        "download_cover": False, "enable_cleaner": True,
    },
    "stealth_mode": {
        "name": "隐身模式", "mode": "incremental", "threads_min": 1, "threads_max": 2,
        "interval_min": 5.0, "interval_max": 15.0, "content_storage": "db",
        "enable_disorder": True, "enable_dedup_by_url": True,
        "enable_cleaner": True, "enable_classifier": True,
    },
}

def get_preset(name: str) -> dict | None:
    return TASK_PRESETS.get(name)

def list_presets() -> list[dict]:
    return [{"key": k, "name": v["name"]} for k, v in TASK_PRESETS.items()]
