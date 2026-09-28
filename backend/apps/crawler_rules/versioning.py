"""Rule version control (v57) — track config changes + rollback."""
from __future__ import annotations
import json
from django.db import models
from django.utils import timezone
from .models import CrawlerRule


class RuleVersion(models.Model):
    """A snapshot of a rule's config at a point in time."""
    rule = models.ForeignKey(CrawlerRule, on_delete=models.CASCADE, related_name="versions")
    version_number = models.IntegerField("版本号", default=1)
    config_snapshot = models.JSONField("配置快照")
    changed_by = models.CharField("修改人", max_length=64, blank=True)
    change_reason = models.CharField("变更原因", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crawler_rule_version"
        verbose_name = "规则版本"
        verbose_name_plural = verbose_name
        ordering = ("-version_number",)
        indexes = [models.Index(fields=["rule", "-version_number"])]

    def __str__(self):
        return f"{self.rule.name} v{self.version_number}"


def save_version(rule: CrawlerRule, changed_by: str = "", reason: str = "") -> RuleVersion:
    """Create a version snapshot of the current rule config."""
    last_version = rule.versions.first()
    next_num = (last_version.version_number + 1) if last_version else 1
    return RuleVersion.objects.create(
        rule=rule, version_number=next_num,
        config_snapshot=rule.config, changed_by=changed_by,
        change_reason=reason,
    )


def rollback_to_version(rule: CrawlerRule, version_number: int) -> bool:
    """Rollback a rule's config to a previous version."""
    try:
        ver = rule.versions.get(version_number=version_number)
    except RuleVersion.DoesNotExist:
        return False
    # Save current as a new version before rollback
    save_version(rule, changed_by="system", reason=f"rollback to v{version_number}")
    rule.config = ver.config_snapshot
    rule.save(update_fields=["config"])
    return True


def version_diff(v1: RuleVersion, v2: RuleVersion) -> dict:
    """Return a simple diff between two rule versions."""
    import difflib
    c1 = json.dumps(v1.config_snapshot, sort_keys=True, indent=2).splitlines()
    c2 = json.dumps(v2.config_snapshot, sort_keys=True, indent=2).splitlines()
    diff = list(difflib.unified_diff(c1, c2, fromfile=f"v{v1.version_number}", tofile=f"v{v2.version_number}", n=1))
    return {"diff": "\n".join(diff), "v1": v1.version_number, "v2": v2.version_number}
