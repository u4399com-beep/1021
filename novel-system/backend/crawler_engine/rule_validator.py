"""Rule validator (v214) — validate rule config before saving/testing."""


REQUIRED_FIELDS = {
    "list": ["item_selector"],
    "book": ["title"],
    "toc": ["item_selector", "chapter_url"],
    "chapter": ["content"],
}


def validate_rule_config(target: str, config: dict) -> dict:
    """Validate a rule config for completeness.
    
    Returns: {valid: bool, missing: [...], warnings: [...]}
    """
    missing = []
    warnings = []
    
    required = REQUIRED_FIELDS.get(target, [])
    for field in required:
        if field not in config or not config[field]:
            missing.append(field)
    
    # Check selector format
    for key, sel in config.items():
        if isinstance(sel, dict) and "type" in sel:
            if sel["type"] not in ("css", "xpath", "regex", "json_path"):
                warnings.append(f"{key}: unknown selector type '{sel['type']}'")
            if not sel.get("expr"):
                warnings.append(f"{key}: empty selector expression")
    
    return {
        "valid": len(missing) == 0,
        "missing": missing,
        "warnings": warnings,
    }
