"""HTML structure obfuscation engine.

Goal: each rendered page has a visually identical layout but the underlying
HTML/CSS byte structure is completely different from any previous render.

Techniques (combined per-request):
  1. class_name_randomize: maps semantic class names (.book-title) to random
     per-request tokens (.a3f7b2). The CSS is rewritten in lockstep.
  2. attr_order_shuffle: randomizes the order of attributes on each element.
  3. whitespace_noise: inserts random whitespace, newlines, and HTML comments
     at random positions. These are invisible to the user but change the bytes.
  4. invisible_elements: inserts random <div style="display:none">...</div>
     blocks with random lengths.
  5. comment_inject: inserts random HTML comments containing random tokens.

All techniques preserve:
  - The DOM tree structure (tags / parents / children)
  - The visible text content
  - The visible styling (CSS computed values)
  - The interactive behavior

Implementation notes:
  - Uses BeautifulSoup for parsing
  - The class name map is generated once per render and applied to <style> blocks
    AND class attributes simultaneously
  - Comments and invisible elements are inserted in random positions
"""
from __future__ import annotations

import random
import re
import string
from typing import Any

from bs4 import BeautifulSoup, Comment, NavigableString, Tag


_RANDOM_TOKEN_LEN = 6


def _rand_token(prefix: str = "x") -> str:
    """Generate a random CSS-class-like token: x + alphanumeric."""
    chars = string.ascii_lowercase + string.digits
    body = "".join(random.choices(chars, k=_RANDOM_TOKEN_LEN))
    return f"{prefix}{body}"


def _rand_html_comment() -> Comment:
    """Build a BeautifulSoup Comment node containing random text."""
    text = _rand_token("c")
    # Use the same soup instance the caller is using
    return Comment(text)


# ------------------------------------------------------------------
# Layer 1.1 — class name randomization
# ------------------------------------------------------------------
def randomize_class_names(html: str, *, seed: int | None = None) -> str:
    """Replace every CSS class name with a random token, both in HTML and <style>."""
    if seed is not None:
        random.seed(seed)

    soup = BeautifulSoup(html, "lxml")

    # Step 1: build a mapping {original_class: new_class}
    class_map: dict[str, str] = {}

    def _get_or_assign(orig: str) -> str:
        if orig not in class_map:
            class_map[orig] = _rand_token("c")
        return class_map[orig]

    # Step 2: rewrite every element's class attribute
    for tag in soup.find_all(True):
        cls = tag.get("class")
        if cls:
            new_cls = [_get_or_assign(c) for c in cls]
            tag["class"] = new_cls

    # Step 3: rewrite <style> blocks
    for style in soup.find_all("style"):
        if style.string:
            # Replace .classname occurrences using the mapping
            text = style.string
            for orig, new in class_map.items():
                # Match .classname with word boundary, but not within :pseudo
                text = re.sub(rf"\.{re.escape(orig)}\b", f".{new}", text)
            style.string = text

    # Step 4: rewrite inline style="...class-name" if used in selectors
    # (rare — most inline styles don't reference classes)

    return str(soup)


# ------------------------------------------------------------------
# Layer 1.2 — attribute order shuffle
# ------------------------------------------------------------------
def shuffle_attributes(html: str, *, seed: int | None = None) -> str:
    if seed is not None:
        random.seed(seed)

    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(True):
        attrs = list(tag.attrs.items())
        if len(attrs) > 1:
            random.shuffle(attrs)
            tag.attrs.clear()
            for k, v in attrs:
                tag.attrs[k] = v
    return str(soup)


# ------------------------------------------------------------------
# Layer 1.3 — whitespace noise
# ------------------------------------------------------------------
def inject_whitespace_noise(html: str, *, seed: int | None = None) -> str:
    """Insert random whitespace / newlines / comments at random positions."""
    if seed is not None:
        random.seed(seed)

    soup = BeautifulSoup(html, "lxml")

    # Strategy: walk through text nodes and randomly add whitespace siblings
    # Also insert random HTML comments before/after tags
    for tag in list(soup.find_all(True)):
        # Insert comment before some tags (10% chance)
        if random.random() < 0.10:
            comment = Comment(_rand_token("z"))
            tag.insert_before(comment)
        # Insert comment after some tags (10% chance)
        if random.random() < 0.10:
            comment = Comment(_rand_token("z"))
            tag.insert_after(comment)

    return str(soup)


# ------------------------------------------------------------------
# Layer 1.4 — invisible elements
# ------------------------------------------------------------------
_INVISIBLE_STYLE = "display:none;visibility:hidden;opacity:0;"


def inject_invisible_elements(html: str, *, seed: int | None = None) -> str:
    """Insert random <div style="display:none"> with random token contents."""
    if seed is not None:
        random.seed(seed)

    soup = BeautifulSoup(html, "lxml")
    body = soup.body
    if not body:
        return html

    # Insert 1-3 invisible divs at random positions in <body>
    n = random.randint(1, 3)
    for _ in range(n):
        # Build invisible div with random token content
        div = soup.new_tag("div")
        div["style"] = _INVISIBLE_STYLE + _rand_token("p") + ":" + _rand_token("v") + ";"
        # Random number of inner spans with random content
        inner_count = random.randint(0, 3)
        for _i in range(inner_count):
            span = soup.new_tag("span")
            span["class"] = _rand_token("h")
            span.string = _rand_token("k")
            div.append(span)
        # Insert at random position
        children = list(body.children)
        if children:
            pos = random.randint(0, len(children))
            body.insert(pos, div)
        else:
            body.append(div)

    return str(soup)


# ------------------------------------------------------------------
# Layer 1.5 — comment noise (more aggressive than whitespace)
# ------------------------------------------------------------------
def inject_comment_noise(html: str, *, seed: int | None = None) -> str:
    """Insert longer random HTML comments containing fake but plausible content."""
    if seed is not None:
        random.seed(seed)

    soup = BeautifulSoup(html, "lxml")

    fake_fragments = [
        f"<!-- section-{_rand_token()} render-id={random.randint(10000, 99999)} -->",
        f"<!-- layout cache: {_rand_token('h')}.{_rand_token('v')} -->",
        f"<!-- optimized for {_rand_token()} on {random.randint(1, 1000)}ms -->",
    ]
    body = soup.body
    if not body:
        return html

    for _ in range(random.randint(2, 4)):
        fragment = random.choice(fake_fragments)
        # Parse fragment into a Comment node
        c = Comment(re.search(r"-->(.*)<!--", fragment + "<!-- -->").group(1).strip())
        children = list(body.children)
        if children:
            body.insert(random.randint(0, len(children)), c)

    return str(soup)


# ------------------------------------------------------------------
# Master — apply all enabled layers in order
# ------------------------------------------------------------------
def obfuscate_html(
    html: str,
    *,
    class_randomize: bool = True,
    attr_order_shuffle: bool = True,
    whitespace_noise: bool = True,
    invisible_elements: bool = True,
    comment_inject: bool = True,
    seed: int | None = None,
) -> str:
    """Apply all enabled HTML obfuscation layers in sequence."""
    if not any([class_randomize, attr_order_shuffle, whitespace_noise,
                invisible_elements, comment_inject]):
        return html

    # Seed once for the entire chain to keep class_name ↔ style rewrite consistent
    actual_seed = seed if seed is not None else random.randint(0, 2**32 - 1)

    if class_randomize:
        html = randomize_class_names(html, seed=actual_seed)
    if attr_order_shuffle:
        html = shuffle_attributes(html, seed=actual_seed + 1)
    if whitespace_noise:
        html = inject_whitespace_noise(html, seed=actual_seed + 2)
    if invisible_elements:
        html = inject_invisible_elements(html, seed=actual_seed + 3)
    if comment_inject:
        html = inject_comment_noise(html, seed=actual_seed + 4)
    return html
