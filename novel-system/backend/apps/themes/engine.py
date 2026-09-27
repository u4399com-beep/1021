"""Theme metadata is stored in `apps.sites.models.Theme`. This app
provides render helpers + theme discovery (static files for each theme).
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string


THEME_TEMPLATES = {
    "simple_reading": {
        "name": "简约阅读",
        "files": ["index.html", "book_detail.html", "chapter.html", "category.html"],
        "static_dir": "themes/simple_reading",
    },
    "classic_shelf": {
        "name": "古典书架",
        "files": ["index.html", "book_detail.html", "chapter.html"],
        "static_dir": "themes/classic_shelf",
    },
    "magazine_modern": {
        "name": "杂志现代",
        "files": ["index.html", "book_detail.html", "chapter.html"],
        "static_dir": "themes/magazine_modern",
    },
    "dark_tech": {
        "name": "暗黑科技",
        "files": ["index.html", "book_detail.html", "chapter.html"],
        "static_dir": "themes/dark_tech",
    },
    "minimal_rank": {
        "name": "极简榜单",
        "files": ["index.html", "book_detail.html", "chapter.html"],
        "static_dir": "themes/minimal_rank",
    },
}


def get_theme_path(theme_code: str) -> Path:
    return Path(settings.BASE_DIR).parent / "themes" / theme_code


def render_theme_page(theme_code: str, page: str, context: dict | None = None) -> str:
    """Render a theme page with Django context.

    Themes live under /themes/<code>/ and are plain HTML+JS+CSS.
    The Django renderer injects SEO context (TDK, JSON-LD).
    """
    theme_dir = get_theme_path(theme_code)
    template_file = theme_dir / f"{page}.html"
    if not template_file.exists():
        return f"<!-- theme {theme_code} page {page} not found -->"
    from django.template import engines
    dj_engine = engines["django"]
    template = dj_engine.from_string(template_file.read_text(encoding="utf-8"))
    return template.render(context or {})
