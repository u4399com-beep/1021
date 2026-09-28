"""Theme-level SEO check — verify each theme's HTML templates include the
required SEO tags (TDK, canonical, geo, schema.org, Open Graph, etc).

This runs as part of the SEO audit panel — when a site uses a theme, the
panel checks the theme's HTML files for required SEO elements.
"""

import re
from pathlib import Path
from typing import Any

from django.conf import settings


# Theme name → expected file list
THEME_FILES = {
    "simple_reading":   ["index.html", "book_detail.html", "chapter.html"],
    "classic_shelf":     ["index.html", "book_detail.html", "chapter.html"],
    "magazine_modern":   ["index.html", "book_detail.html", "chapter.html"],
    "dark_tech":         ["index.html", "book_detail.html", "chapter.html"],
    "minimal_rank":      ["index.html", "book_detail.html", "chapter.html"],
}


# Required SEO elements (regex against the HTML source)
REQUIRED_SEO_PATTERNS = [
    ("title_tag",         r"<title[^>]*>.+</title>",                                   "页面必须有 <title>"),
    ("meta_description",  r'<meta\s+name=["\']description["\']',                          "页面必须有 description meta"),
    ("meta_keywords",     r'<meta\s+name=["\']keywords["\']',                            "页面必须有 keywords meta"),
    ("meta_viewport",     r'<meta\s+name=["\']viewport["\']',                            "页面必须有 viewport meta（移动端适配）"),
    ("canonical",        r'<link\s+rel=["\']canonical["\']',                            "页面必须有 canonical 链接"),
    ("og_title",          r'<meta\s+property=["\']og:title["\']',                         "页面必须有 og:title"),
    ("og_description",    r'<meta\s+property=["\']og:description["\']',                  "页面必须有 og:description"),
    ("og_type",           r'<meta\s+property=["\']og:type["\']',                          "页面必须有 og:type"),
    ("og_locale",         r'<meta\s+property=["\']og:locale["\']',                        "页面必须有 og:locale"),
    ("geo_region",        r'<meta\s+name=["\']geo.region["\']',                           "页面必须有 geo.region"),
    ("language_meta",     r'<meta\s+name=["\']language["\']|<html[^>]+lang=',             "页面必须有 lang 声明"),
    ("schema_org",        r'application/ld\+json',                                      "页面必须有 Schema.org 结构化数据"),
]


def check_theme_files(theme_code: str) -> dict[str, Any]:
    """Return per-file SEO check report for a theme.

    Output: {
      theme_code,
      files_total,
      files_present,
      issues: [
        {file, check, ok, message},
        ...
      ],
    }
    """
    themes_root = Path(settings.BASE_DIR).parent / "themes"
    theme_dir = themes_root / theme_code
    files = THEME_FILES.get(theme_code, [])

    issues = []
    files_present = 0
    for filename in files:
        fpath = theme_dir / filename
        if not fpath.exists():
            issues.append({
                "file": filename, "check": "exists",
                "ok": False, "message": f"文件不存在: {filename}",
            })
            continue
        files_present += 1
        content = fpath.read_text(encoding="utf-8")
        for check_name, pattern, message in REQUIRED_SEO_PATTERNS:
            ok = bool(re.search(pattern, content, re.IGNORECASE))
            if not ok:
                issues.append({
                    "file": filename, "check": check_name,
                    "ok": False, "message": message,
                })

    return {
        "theme_code": theme_code,
        "files_total": len(files),
        "files_present": files_present,
        "issues_count": len(issues),
        "issues": issues,
        "score": round((files_present * len(REQUIRED_SEO_PATTERNS) - len(issues)) /
                       (max(1, len(files) * len(REQUIRED_SEO_PATTERNS))) * 100, 1),
    }


def check_all_themes() -> list[dict[str, Any]]:
    """Return SEO check report for all 5 themes."""
    return [check_theme_files(code) for code in THEME_FILES.keys()]
