"""Theme plugin system — users can upload custom themes as ZIP files.

Each theme ZIP must contain at minimum:
  - theme.json   — manifest with code, name, description
  - index.html   — homepage template (uses Django template syntax)
  - assets/style.css   — main stylesheet

Optional:
  - book_detail.html
  - chapter.html
  - category.html
  - assets/*.css / *.js / images/*

On upload, the theme is extracted to /themes/<code>/ and a Theme record
is created in the DB.

Validation:
  - theme.json must exist and parse
  - index.html must exist
  - code must be a valid slug (lowercase + dashes)
  - code must not collide with built-in themes
"""

import json
import os
import re
import shutil
import zipfile
from pathlib import Path

from django.conf import settings
from loguru import logger

from apps.sites.models import Theme


BUILTIN_THEMES = {"simple_reading", "classic_shelf", "magazine_modern", "dark_tech", "minimal_rank"}
THEMES_ROOT = Path(settings.BASE_DIR).parent / "themes"


def _validate_theme_code(code: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9_-]{2,30}$", code or ""))


def validate_zip(zip_path: Path) -> dict:
    """Validate a theme ZIP and return its manifest.

    Returns:
      {
        ok: bool,
        manifest: dict | None,
        errors: [str, ...]
      }
    """
    errors = []
    manifest = None
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()

            # Avoid path traversal
            for n in names:
                if n.startswith("/") or ".." in n:
                    errors.append(f"path traversal detected: {n}")
                    return {"ok": False, "manifest": None, "errors": errors}

            # Find theme.json (at root or in a single nested dir)
            manifest_name = None
            for n in names:
                if n == "theme.json" or n.endswith("/theme.json"):
                    # Must be exactly at root or one dir deep
                    parts = n.split("/")
                    if len(parts) == 1 or len(parts) == 2:
                        manifest_name = n
                        break
            if not manifest_name:
                errors.append("theme.json not found at root (or one dir deep)")
                return {"ok": False, "manifest": None, "errors": errors}

            try:
                manifest = json.loads(z.read(manifest_name))
            except json.JSONDecodeError as e:
                errors.append(f"theme.json invalid JSON: {e!r}")
                return {"ok": False, "manifest": None, "errors": errors}

            # Validate required fields
            code = manifest.get("code", "")
            if not _validate_theme_code(code):
                errors.append(f"theme code invalid: {code!r} (must be lowercase + dashes, 3-30 chars)")
            if code in BUILTIN_THEMES:
                errors.append(f"code '{code}' collides with built-in theme")
            if not manifest.get("name"):
                errors.append("theme.json missing 'name'")

            # Validate index.html exists
            has_index = any(
                n == "index.html" or n.endswith("/index.html")
                for n in names
            )
            if not has_index:
                errors.append("index.html not found")

            if errors:
                return {"ok": False, "manifest": manifest, "errors": errors}

            return {"ok": True, "manifest": manifest, "errors": []}
    except zipfile.BadZipFile as e:
        return {"ok": False, "manifest": None, "errors": [f"bad zip: {e!r}"]}


def install_theme_zip(zip_path: Path, *, overwrite: bool = False) -> dict:
    """Install a theme ZIP to /themes/<code>/ and create DB record.

    Returns:
      {
        ok: bool,
        theme_id: int | None,
        code: str | None,
        errors: [str, ...]
      }
    """
    validation = validate_zip(zip_path)
    if not validation["ok"]:
        return {"ok": False, "theme_id": None, "code": None, "errors": validation["errors"]}

    manifest = validation["manifest"]
    code = manifest["code"]

    # Check existing theme
    if Theme.objects.filter(code=code).exists() and not overwrite:
        return {"ok": False, "theme_id": None, "code": code,
                "errors": [f"theme '{code}' already exists; use overwrite=True"]}

    # Extract to /themes/<code>/
    target = THEMES_ROOT / code
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            # Find the root prefix (if theme files are nested in a single dir)
            names = z.namelist()
            prefix = ""
            if names and "/" in names[0]:
                first_parts = names[0].split("/")
                # If first part is a single dir name, use it as prefix
                if all(n.startswith(first_parts[0] + "/") for n in names):
                    prefix = first_parts[0] + "/"
            for n in names:
                if n.endswith("/"):
                    continue
                target_path = target / n[len(prefix):]
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(z.read(n))
    except Exception as e:
        shutil.rmtree(target, ignore_errors=True)
        return {"ok": False, "theme_id": None, "code": code, "errors": [f"extract failed: {e!r}"]}

    # Create or update DB record
    theme, _ = Theme.objects.update_or_create(
        code=code,
        defaults={
            "name": manifest.get("name", code),
            "description": manifest.get("description", ""),
            "preview": manifest.get("preview", ""),
            "is_active": True,
        },
    )

    logger.info(f"theme installed: {code} → {target}")
    return {"ok": True, "theme_id": theme.id, "code": code, "errors": []}


def list_themes_on_disk() -> list[dict]:
    """List all theme directories on disk (built-in + custom)."""
    if not THEMES_ROOT.exists():
        return []
    result = []
    for d in sorted(THEMES_ROOT.iterdir()):
        if not d.is_dir():
            continue
        manifest_path = d / "theme.json"
        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        files = [f.name for f in d.iterdir() if f.is_file()] + \
                [f"assets/{f.name}" for f in (d / "assets").iterdir() if (d / "assets").is_dir() and f.is_file()]
        result.append({
            "code": d.name,
            "name": manifest.get("name", d.name),
            "description": manifest.get("description", ""),
            "is_builtin": d.name in BUILTIN_THEMES,
            "files": files,
        })
    return result


def delete_custom_theme(code: str) -> dict:
    """Delete a custom theme directory + DB record. Cannot delete built-ins."""
    if code in BUILTIN_THEMES:
        return {"ok": False, "error": "cannot delete built-in theme"}
    target = THEMES_ROOT / code
    if target.exists():
        shutil.rmtree(target)
    Theme.objects.filter(code=code).delete()
    return {"ok": True, "deleted_code": code}


def create_sample_theme_zip(out_path: Path, *, code: str = "my_custom_theme", name: str = "我的自定义主题") -> Path:
    """Generate a sample theme ZIP for users to download as a template."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        # theme.json
        manifest = {
            "code": code, "name": name,
            "description": "示例自定义主题模板",
            "preview": "",
        }
        z.writestr("theme.json", json.dumps(manifest, indent=2, ensure_ascii=False))

        # index.html — minimal viable theme
        z.writestr("index.html", """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{{ site.site_title|default:"我的小说站" }}</title>
  <meta name="description" content="{{ site.site_description }}">
  <meta name="keywords" content="{{ site.site_keywords }}">
  <link rel="canonical" href="{{ request.build_absolute_uri }}">
  <link rel="stylesheet" href="./assets/style.css">
  {{ site.head_inject|safe }}
</head>
<body>
  <header>
    <h1>{{ site.name|default:"我的小说站" }}</h1>
  </header>
  <main>
    <h2>最新小说</h2>
    <ul>
      {% for book in latest_books %}
      <li>
        <a href="/book/{{ book.slug }}">{{ book.title }}</a>
        — {{ book.author.name|default:"佚名" }}
      </li>
      {% endfor %}
    </ul>
  </main>
  <footer>
    <p>&copy; {{ now|date:"Y" }} {{ site.name }}</p>
  </footer>
  {{ site.body_inject|safe }}
</body>
</html>""")

        # assets/style.css — minimal sample
        z.writestr("assets/style.css", """body { font-family: 'Noto Sans SC', sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
header { border-bottom: 2px solid #409eff; padding: 16px 0; }
footer { margin-top: 40px; text-align: center; color: #909399; }
ul { list-style: none; padding: 0; }
li { padding: 8px 0; border-bottom: 1px dashed #ebeef5; }
li a { color: #409eff; text-decoration: none; }""")

    return out_path
