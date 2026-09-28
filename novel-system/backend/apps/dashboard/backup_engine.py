"""Automated backup (v37) — daily export of critical tables + uploads.

Goals:
  - Run via celery beat (daily at 03:30 AM)
  - Export critical tables to JSON (subset of fields for size)
  - Compress with gzip
  - Optional upload to S3-compatible object storage

Configuration:
  BACKUP_ENABLED=true (env) — enable auto-backups
  BACKUP_LOCAL_DIR=/app/media/backups
  BACKUP_S3_BUCKET=my-backups (optional)
  BACKUP_S3_REGION=us-east-1
  BACKUP_S3_PREFIX=novel-system/
  BACKUP_RETENTION_DAYS=30
"""

import gzip
import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from loguru import logger


def get_backup_dir() -> Path:
    backup_dir = Path(
        getattr(settings, "BACKUP_LOCAL_DIR", None) or
        str(Path(settings.MEDIA_ROOT) / "backups")
    )
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def is_backup_enabled() -> bool:
    return getattr(settings, "BACKUP_ENABLED", False)


def backup_database_dump(target_path: Path) -> Path:
    """Run pg_dump equivalent via Django dumpdata.

    Exports all model records as JSON fixture.
    """
    with open(target_path, "w", encoding="utf-8") as f:
        call_command("dumpdata", "--natural-foreign", "--natural-primary",
                     "--exclude=contenttypes", "--exclude=auth.permission",
                     stdout=f, format="json", indent=2)
    return target_path


def backup_critical_tables(target_dir: Path, *, ts_str: str) -> list[Path]:
    """Per-table JSON export of the most critical tables."""
    apps_to_dump = [
        ("novel", "novel.Book"),
        ("novel", "novel.Volume"),
        ("novel", "novel.Chapter"),
        ("novel", "novel.Author"),
        ("novel", "novel.Category"),
        ("novel", "novel.Tag"),
        ("crawler_rules", "crawler_rules.CrawlerRule"),
        ("crawler_rules", "crawler_rules.CrawlerSource"),
        ("crawler_tasks", "crawler_tasks.CrawlerTask"),
        ("account", "account.User"),
        ("account", "account.Role"),
        ("sites", "sites.Site"),
        ("sites", "sites.Theme"),
        ("obfuscator", "obfuscator.ObfuscationProfile"),
        ("smart_classifier", "smart_classifier.CategoryKeyword"),
        ("content_cleaner", "content_cleaner.CleaningRule"),
        ("file_download", "file_download.DownloadTemplate"),
    ]
    written = []
    for app_label, model_label in apps_to_dump:
        out = target_dir / f"{ts_str}_{model_label.replace('.', '_')}.json"
        try:
            with open(out, "w", encoding="utf-8") as f:
                call_command("dumpdata", model_label, stdout=f, format="json", indent=2)
            written.append(out)
        except Exception as e:
            logger.warning(f"failed to backup {model_label}: {e!r}")
    return written


def gzip_file(src: Path, dst: Path | None = None) -> Path:
    dst = dst or src.with_suffix(src.suffix + ".gz")
    with open(src, "rb") as fin, gzip.open(dst, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    return dst


def gzip_directory(src_dir: Path, dst_archive: Path) -> Path:
    """Compress an entire directory into a single .tar.gz file."""
    import tarfile
    with tarfile.open(dst_archive, "w:gz") as tar:
        tar.add(src_dir, arcname=src_dir.name)
    return dst_archive


def cleanup_old_backups(retention_days: int = 30) -> int:
    """Delete backup files older than retention_days. Returns count deleted."""
    backup_dir = get_backup_dir()
    cutoff = timezone.now() - timedelta(days=retention_days)
    deleted = 0
    for f in backup_dir.iterdir():
        if not f.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.get_current_timezone())
            if mtime < cutoff:
                f.unlink()
                deleted += 1
                logger.info(f"deleted old backup: {f.name}")
        except Exception as e:
            logger.warning(f"failed to stat {f}: {e!r}")
    return deleted


def upload_to_s3(local_path: Path, key: str) -> str | None:
    """Upload a backup file to S3-compatible storage. Returns the s3 URL."""
    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not installed — skipping S3 upload")
        return None
    bucket = getattr(settings, "BACKUP_S3_BUCKET", "")
    region = getattr(settings, "BACKUP_S3_REGION", "us-east-1")
    prefix = getattr(settings, "BACKUP_S3_PREFIX", "novel-system/")
    if not bucket:
        return None
    try:
        s3 = boto3.client("s3", region_name=region)
        s3.upload_file(str(local_path), bucket, f"{prefix}{key}")
        return f"s3://{bucket}/{prefix}{key}"
    except Exception as e:
        logger.warning(f"S3 upload failed: {e!r}")
        return None


def run_backup() -> dict:
    """Main entry point — run a full backup cycle.

    Returns: {
      ts: str,
      local_dir: str,
      per_table_files: [str, ...],
      full_dump_path: str,
      archive_path: str,
      s3_url: str | None,
      cleaned_up_count: int,
      duration_seconds: float,
    }
    """
    t0 = time.time()
    ts = timezone.now()
    ts_str = ts.strftime("%Y%m%d_%H%M%S")
    backup_dir = get_backup_dir()
    target_dir = backup_dir / ts_str
    target_dir.mkdir(exist_ok=True)

    # 1. Critical tables (per-table JSON)
    per_table_files = backup_critical_tables(target_dir, ts_str=ts_str)

    # 2. Full DB dump
    full_dump_path = target_dir / f"{ts_str}_full_dump.json"
    backup_database_dump(full_dump_path)

    # 3. Compress each per-table file
    compressed = []
    for f in per_table_files:
        gz = gzip_file(f)
        compressed.append(gz)
        f.unlink()  # remove uncompressed
    full_dump_gz = gzip_file(full_dump_path)
    full_dump_path.unlink()
    compressed.append(full_dump_gz)

    # 4. Tar.gz archive of the whole dir
    archive_path = backup_dir / f"{ts_str}_backup.tar.gz"
    gzip_directory(target_dir, archive_path)

    # 5. Optional S3 upload
    s3_url = None
    if getattr(settings, "BACKUP_S3_BUCKET", ""):
        s3_url = upload_to_s3(archive_path, archive_path.name)

    # 6. Cleanup old backups
    retention_days = int(getattr(settings, "BACKUP_RETENTION_DAYS", 30))
    cleaned = cleanup_old_backups(retention_days)

    duration = time.time() - t0
    logger.info(f"backup complete in {duration:.1f}s → {archive_path}")

    return {
        "ts": ts.isoformat(),
        "local_dir": str(backup_dir),
        "archive_path": str(archive_path),
        "archive_size_bytes": archive_path.stat().st_size,
        "per_table_files": [str(f) for f in compressed],
        "s3_url": s3_url,
        "cleaned_up_count": cleaned,
        "duration_seconds": round(duration, 2),
    }


def diagnostics() -> dict:
    return {
        "enabled": is_backup_enabled(),
        "backup_dir": str(get_backup_dir()),
        "s3_configured": bool(getattr(settings, "BACKUP_S3_BUCKET", "")),
        "retention_days": int(getattr(settings, "BACKUP_RETENTION_DAYS", 30)),
    }
