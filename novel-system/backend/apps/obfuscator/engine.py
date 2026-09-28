"""Obfuscator master engine — apply all three layers to a rendered HTML response.

Used by:
  - `apps.obfuscator.middleware.ObfuscatorMiddleware` (post-process responses)
  - `apps.obfuscator.templatetags.obfuscator_tags.obfuscate` template tag
  - Direct API calls from theme renderers
"""

import random
from typing import Optional

from apps.sites.models import Site

from .html_obfuscator import obfuscate_html as _obfuscate_html
from .models import ObfuscationProfile
from .rewriter import rewrite_html_content
from .transcoder import transcode_html_content


def get_profile(site: Site) -> Optional[ObfuscationProfile]:
    """Get or create the obfuscation profile for a site."""
    if not site:
        return None
    profile, _ = ObfuscationProfile.objects.get_or_create(site=site)
    return profile


def apply_obfuscation(html: str, *, site: Site | None = None, book=None, chapter=None) -> str:
    """Apply all enabled obfuscation layers based on the site's profile.

    Each call uses a fresh random seed so consecutive renders of the same
    page produce structurally unique HTML.
    """
    if not html:
        return html

    profile = get_profile(site) if site else None
    if not profile or not profile.enabled:
        return html

    # Generate a per-request seed
    seed = random.randint(0, 2**32 - 1) if profile.seed_per_request else None

    # ─── Layer 1: HTML structure obfuscation ────────────────
    html = _obfuscate_html(
        html,
        class_randomize=profile.html_class_randomize,
        attr_order_shuffle=profile.html_attr_order_shuffle,
        whitespace_noise=profile.html_whitespace_noise,
        invisible_elements=profile.html_invisible_elements,
        comment_inject=profile.html_comment_inject,
        seed=seed,
    )

    # ─── Layer 2: Text transcoding ─────────────────────────
    html = transcode_html_content(
        html,
        full_width=profile.transcode_full_width,
        homoglyph=profile.transcode_homoglyph,
        zero_width=profile.transcode_zero_width,
        punctuation=profile.transcode_punctuation,
        density=profile.transcode_density,
        seed=seed + 100 if seed is not None else None,
    )

    # ─── Layer 3: Pseudo-original rewriting ─────────────────
    if profile.rewrite_synonym or profile.rewrite_sentence_reorder or profile.rewrite_interference:
        html = rewrite_html_content(
            html,
            site=site, book=book, chapter=chapter,
            synonym=profile.rewrite_synonym,
            reorder=profile.rewrite_sentence_reorder,
            interference=profile.rewrite_interference,
            synonym_density=0.4,
            interference_density=profile.rewrite_interference_density,
            seed=seed + 200 if seed is not None else None,
        )

    return html


def apply_text_only(text: str, *, site: Site | None = None) -> str:
    """Apply only Layer 2 + Layer 3 to plain text (no HTML structure work).

    Useful for chapter content stored as plain text (TXT downloads, RSS descriptions, etc.)
    """
    if not text:
        return text
    profile = get_profile(site) if site else None
    if not profile or not profile.enabled:
        return text

    seed = random.randint(0, 2**32 - 1) if profile.seed_per_request else None

    # Layer 2: transcoding
    text = transcode_html_content(
        text,
        full_width=profile.transcode_full_width,
        homoglyph=profile.transcode_homoglyph,
        zero_width=profile.transcode_zero_width,
        punctuation=profile.transcode_punctuation,
        density=profile.transcode_density,
        seed=seed,
    )

    # Layer 3: rewriting
    if profile.rewrite_synonym or profile.rewrite_sentence_reorder or profile.rewrite_interference:
        text = rewrite_html_content(
            text,
            site=site,
            synonym=profile.rewrite_synonym,
            reorder=profile.rewrite_sentence_reorder,
            interference=profile.rewrite_interference,
            interference_density=profile.rewrite_interference_density,
            seed=seed + 200 if seed is not None else None,
        )

    return text
