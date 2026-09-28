"""Batch rule testing (v93) — test all rules for a source at once."""
from apps.crawler_rules.models import CrawlerRule, CrawlerSource

def batch_test_source(source_id: int, test_url: str = "") -> dict:
    """Test all enabled rules for a source."""
    rules = CrawlerRule.objects.filter(source_id=source_id, enabled=True)
    results = []
    for rule in rules:
        results.append({
            "rule_id": rule.id, "name": rule.name, "target": rule.target,
            "has_config": bool(rule.config),
            "last_test_at": rule.last_test_at.isoformat() if rule.last_test_at else None,
        })
    return {"source_id": source_id, "rules_tested": len(results), "results": results}
