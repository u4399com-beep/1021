"""Rule import/export (v62) — JSON package format for sharing rules between instances."""
import json
from .models import CrawlerRule, CrawlerSource


def export_rules(source_id: int | None = None) -> dict:
    """Export rules (optionally for one source) as a JSON-serializable dict."""
    sources_qs = CrawlerSource.objects.all()
    if source_id:
        sources_qs = sources_qs.filter(id=source_id)
    
    package = {
        "format": "novel-system-rules-v1",
        "exported_at": None,  # set by caller
        "sources": [],
        "rules": [],
    }
    
    for src in sources_qs:
        package["sources"].append({
            "name": src.name, "host": src.host,
            "enabled": src.enabled, "anti_detection": src.anti_detection,
            "notes": src.notes,
        })
        for rule in src.rules.all():
            package["rules"].append({
                "source_host": src.host,
                "name": rule.name, "target": rule.target,
                "config": rule.config, "enabled": rule.enabled,
                "priority": rule.priority, "notes": rule.notes,
            })
    
    return package


def import_rules(package: dict, overwrite: bool = False) -> dict:
    """Import rules from a package dict. Returns {imported, skipped, errors}."""
    if package.get("format") != "novel-system-rules-v1":
        return {"error": "unsupported format"}
    
    imported, skipped, errors = 0, 0, []
    host_to_source = {}
    
    for src_data in package.get("sources", []):
        src, created = CrawlerSource.objects.update_or_create(
            host=src_data["host"],
            defaults={
                "name": src_data["name"],
                "enabled": src_data.get("enabled", True),
                "anti_detection": src_data.get("anti_detection", {}),
                "notes": src_data.get("notes", ""),
            },
        )
        host_to_source[src.host] = src
        imported += 1 if created else 0
    
    for rule_data in package.get("rules", []):
        host = rule_data.get("source_host", "")
        src = host_to_source.get(host)
        if not src:
            errors.append(f"source not found: {host}")
            continue
        existing = CrawlerRule.objects.filter(name=rule_data["name"], source=src).first()
        if existing and not overwrite:
            skipped += 1
            continue
        CrawlerRule.objects.update_or_create(
            name=rule_data["name"], source=src,
            defaults={
                "target": rule_data["target"],
                "config": rule_data["config"],
                "enabled": rule_data.get("enabled", True),
                "priority": rule_data.get("priority", 100),
                "notes": rule_data.get("notes", ""),
            },
        )
        imported += 1
    
    return {"imported": imported, "skipped": skipped, "errors": errors}
