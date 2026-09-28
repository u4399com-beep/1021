"""Obfuscation diff tool — compare original vs obfuscated HTML byte-by-byte.

Used by the admin "preview" page and as an end-to-end test tool.
"""

import difflib
from typing import Any

from apps.sites.models import Site

from .engine import apply_obfuscation


def render_twice(site: Site, sample_html: str) -> dict[str, Any]:
    """Render the same HTML twice through obfuscation and compare.

    Returns:
        {
          "original":           original HTML,
          "render1":            first obfuscated version,
          "render2":            second obfuscated version,
          "render1_size":       bytes,
          "render2_size":       bytes,
          "byte_diff_count":   number of differing bytes between render1 and render2,
          "structural_similarity": 0.0-1.0 (1.0 = identical structure),
          "byte_similarity":   0.0-1.0 (1.0 = identical bytes),
          "diff_lines":        unified diff lines
        }
    """
    r1 = apply_obfuscation(sample_html, site=site)
    r2 = apply_obfuscation(sample_html, site=site)

    # Byte-level similarity via difflib
    sm = difflib.SequenceMatcher(a=r1.encode("utf-8"), b=r2.encode("utf-8"))
    byte_sim = sm.ratio()
    byte_diff = sum(1 for a, b in zip(r1.encode("utf-8"), r2.encode("utf-8")) if a != b)

    # Structural similarity — compare tag sequence only
    import re
    tags1 = re.findall(r"<[^>]+>", r1)
    tags2 = re.findall(r"<[^>]+>", r2)
    tag_sm = difflib.SequenceMatcher(a=tags1, b=tags2)
    structural_sim = tag_sm.ratio()

    # Unified diff (first 100 lines for display)
    diff_lines = list(difflib.unified_diff(
        r1.splitlines(keepends=False),
        r2.splitlines(keepends=False),
        fromfile="render1",
        tofile="render2",
        n=1,
    ))[:100]

    return {
        "original": sample_html,
        "render1": r1,
        "render2": r2,
        "render1_size": len(r1.encode("utf-8")),
        "render2_size": len(r2.encode("utf-8")),
        "byte_diff_count": byte_diff,
        "byte_similarity": round(byte_sim, 4),
        "structural_similarity": round(structural_sim, 4),
        "tags_in_render1": len(tags1),
        "tags_in_render2": len(tags2),
        "diff_lines": diff_lines,
    }


def render_visual_diff(site: Site, sample_html: str) -> dict:
    """Render an HTML diff that highlights changes between two renders.

    Useful for embedding in the admin UI to show users *what* the
    obfuscator actually changed.
    """
    r1 = apply_obfuscation(sample_html, site=site)
    r2 = apply_obfuscation(sample_html, site=site)
    diff_html = difflib.HtmlDiff().make_table(
        r1.splitlines(),
        r2.splitlines(),
        fromdesc="Render #1",
        todesc="Render #2",
        context=True,
    )
    return {
        "render1": r1,
        "render2": r2,
        "diff_html": diff_html,
    }
