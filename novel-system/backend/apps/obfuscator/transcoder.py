"""Text transcoding engine — byte-level transformations preserving visual identity.

Goal: make the rendered Chinese text byte-different but visually equivalent,
to evade keyword-based audit/review mechanisms used by search engines and
content monitoring systems.

Layers:
  1. full_width: 半角 → 全角 (e.g., 'a' → 'ａ', '1' → '１')
  2. homoglyph: Latin letters → Cyrillic / Greek lookalikes
  3. zero_width: Insert zero-width characters between code points
  4. punctuation: 句号 → ．. ， → 、  ！ → !  " → 〝〞 等标点变体

Each transformation is applied with `density` probability per character,
so the output preserves partial similarity to the original — important
because pure 100% transformation may itself become detectable.
"""

import random
import re
import unicodedata


# ─── Homoglyph maps ───────────────────────────────────────────────
# Latin → Cyrillic look-alikes (Unicode confusables)
LATIN_TO_CYRILLIC = {
    "a": "а", "A": "А", "B": "В", "c": "с", "C": "С",
    "e": "е", "E": "Е", "H": "Н", "K": "К", "M": "М",
    "o": "о", "O": "О", "p": "р", "P": "Р", "T": "Т",
    "x": "х", "X": "Х", "y": "у", "Y": "У",
}

# Latin → Greek look-alikes
LATIN_TO_GREEK = {
    "a": "α", "A": "Α", "B": "Β", "E": "Ε", "Z": "Ζ",
    "H": "Η", "I": "Ι", "K": "Κ", "M": "Μ", "N": "Ν",
    "O": "Ο", "P": "Ρ", "T": "Τ", "X": "Χ", "Y": "Υ",
}

# Punctuation variants — Unicode has many equivalents
PUNCT_VARIANTS = {
    "，": [",", "，", "、"],
    "。": ["。", "．", "."],
    "！": ["!", "！", "❗"],
    "？": ["?", "？", "❓"],
    "：": [":", "：", "﹕"],
    "；": [";", "；", "﹔"],
    "「": ["「", "「", "「"],
    "」": ["」", "」", "」"],
    "“": ["“", "〝", "＂"],
    "”": ["”", "〞", "＂"],
    "‘": ["‘", "‹", "＜"],
    "’": ["’", "›", "＞"],
    "—": ["—", "─", "──"],
    "…": ["…", "···", "..."],
}

# Zero-width characters
ZERO_WIDTH_CHARS = ["\u200b", "\u200c", "\u200d", "\ufeff"]


# ─── Single-char transformations ─────────────────────────────────
def _to_full_width(ch: str) -> str:
    """ASCII → full-width form."""
    try:
        return unicodedata.normalize("NFKC", ch).translate({
            0x21: 0xFF01, 0x22: 0xFF02, 0x23: 0xFF03, 0x24: 0xFF04, 0x25: 0xFF05,
            0x26: 0xFF06, 0x27: 0xFF07, 0x28: 0xFF08, 0x29: 0xFF09, 0x2A: 0xFF0A,
            0x2B: 0xFF0B, 0x2C: 0xFF0C, 0x2D: 0xFF0D, 0x2E: 0xFF0E, 0x2F: 0xFF0F,
            0x30: 0xFF10, 0x31: 0xFF11, 0x32: 0xFF12, 0x33: 0xFF13, 0x34: 0xFF14,
            0x35: 0xFF15, 0x36: 0xFF16, 0x37: 0xFF17, 0x38: 0xFF18, 0x39: 0xFF19,
            0x3A: 0xFF1A, 0x3B: 0xFF1B, 0x3C: 0xFF1C, 0x3D: 0xFF1D, 0x3E: 0xFF1E,
            0x3F: 0xFF1F, 0x40: 0xFF20,
            0x41: 0xFF21, 0x42: 0xFF22, 0x43: 0xFF23, 0x44: 0xFF24, 0x45: 0xFF25,
            0x46: 0xFF26, 0x47: 0xFF27, 0x48: 0xFF28, 0x49: 0xFF29, 0x4A: 0xFF2A,
            0x4B: 0xFF2B, 0x4C: 0xFF2C, 0x4D: 0xFF2D, 0x4E: 0xFF2E, 0x4F: 0xFF2F,
            0x50: 0xFF30, 0x51: 0xFF31, 0x52: 0xFF32, 0x53: 0xFF33, 0x54: 0xFF34,
            0x55: 0xFF35, 0x56: 0xFF36, 0x57: 0xFF37, 0x58: 0xFF38, 0x59: 0xFF39,
            0x5A: 0xFF3A,
            0x61: 0xFF41, 0x62: 0xFF42, 0x63: 0xFF43, 0x64: 0xFF44, 0x65: 0xFF45,
            0x66: 0xFF46, 0x67: 0xFF47, 0x68: 0xFF48, 0x69: 0xFF49, 0x6A: 0xFF4A,
            0x6B: 0xFF4B, 0x6C: 0xFF4C, 0x6D: 0xFF4D, 0x6E: 0xFF4E, 0x6F: 0xFF4F,
            0x70: 0xFF50, 0x71: 0xFF51, 0x72: 0xFF52, 0x73: 0xFF53, 0x74: 0xFF54,
            0x75: 0xFF55, 0x76: 0xFF56, 0x77: 0xFF57, 0x78: 0xFF58, 0x79: 0xFF59,
            0x7A: 0xFF5A,
        })
    except Exception:
        return ch


def _to_homoglyph(ch: str) -> str:
    """Latin letter → Cyrillic look-alike."""
    if ch in LATIN_TO_CYRILLIC and random.random() < 0.5:
        return LATIN_TO_CYRILLIC[ch]
    if ch in LATIN_TO_GREEK:
        return LATIN_TO_GREEK[ch]
    return ch


def _to_zero_width_pair(ch: str) -> str:
    """Insert a random zero-width char after this character."""
    return ch + random.choice(ZERO_WIDTH_CHARS)


def _to_punct_variant(ch: str) -> str:
    """Replace punctuation with one of its Unicode variants."""
    if ch in PUNCT_VARIANTS:
        return random.choice(PUNCT_VARIANTS[ch])
    return ch


# ─── Per-text transcoder ─────────────────────────────────────────
def transcode(
    text: str,
    *,
    full_width: bool = False,
    homoglyph: bool = False,
    zero_width: bool = False,
    punctuation: bool = True,
    density: float = 0.15,
    seed: int | None = None,
) -> str:
    """Apply all enabled transcoding layers with `density` probability per char.

    Args:
        text: input text (any language, but most effects target CJK + Latin)
        full_width: if True, half-width chars may be converted to full-width
        homoglyph: if True, Latin letters may be converted to Cyrillic/Greek lookalikes
        zero_width: if True, zero-width chars inserted between code points
        punctuation: if True, punctuation chars may be swapped with variants
        density: 0.0~1.0, per-char probability of being transcoded
        seed: optional random seed for reproducibility

    Returns: transcoded text (visually identical, byte-different)
    """
    if not text:
        return text
    if seed is not None:
        random.seed(seed)
    if density <= 0:
        return text

    out_chars = []
    for ch in text:
        # Skip whitespace and newlines
        if ch in (" ", "\n", "\r", "\t"):
            out_chars.append(ch)
            continue

        # Skip HTML tag chars (don't transcode HTML)
        # (handled in caller — here we operate on plain text only)

        new_ch = ch
        applied = False

        if punctuation and ch in PUNCT_VARIANTS and random.random() < density:
            new_ch = _to_punct_variant(ch)
            applied = True

        if not applied and full_width and random.random() < density:
            new_ch = _to_full_width(new_ch)
            applied = True

        if not applied and homoglyph and random.random() < density:
            new_ch = _to_homoglyph(new_ch)

        out_chars.append(new_ch)

        if zero_width and random.random() < density:
            out_chars.append(random.choice(ZERO_WIDTH_CHARS))

    return "".join(out_chars)


# ─── HTML-aware transcoder (preserves tags) ──────────────────────
def transcode_html_content(
    html: str,
    *,
    full_width: bool = False,
    homoglyph: bool = False,
    zero_width: bool = False,
    punctuation: bool = True,
    density: float = 0.15,
    seed: int | None = None,
) -> str:
    """Transcode only the visible text in HTML, leaving tags/attributes intact."""
    if not html:
        return html
    if seed is not None:
        random.seed(seed)

    # Split HTML into "in-tag" and "text" segments using a simple regex
    # This avoids needing BeautifulSoup for performance, and handles typical
    # novel chapter HTML (<p>, <br>, etc.) without surprises.
    parts = re.split(r"(<[^>]+>)", html)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 1:
            # in-tag — keep as-is
            out.append(p)
        else:
            out.append(transcode(
                p,
                full_width=full_width, homoglyph=homoglyph,
                zero_width=zero_width, punctuation=punctuation,
                density=density,
            ))
    return "".join(out)
