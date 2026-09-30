"""Pagination + redirect + encoding handler (v139)."""
import re
from loguru import logger


def follow_pagination(fetch_fn, start_url: str, next_page_selector: dict,
                      max_pages: int = 50, base_url: str = "") -> list[str]:
    """Follow pagination links and collect all page URLs.

    Args:
        fetch_fn: callable that takes URL and returns HTML
        start_url: first page URL
        next_page_selector: selector dict for the "next page" link
        max_pages: safety cap
        base_url: base for resolving relative URLs

    Returns: list of all page URLs visited (including start_url)
    """
    from .selectors import SelectorSpec, apply, _parse_html
    
    urls = [start_url]
    current_url = start_url
    spec = SelectorSpec.from_dict(next_page_selector)
    spec.base_url = base_url or start_url
    
    for _ in range(max_pages - 1):
        try:
            html = fetch_fn(current_url)
            tree = _parse_html(html)
            next_url = apply(spec, tree)
            if not next_url or not isinstance(next_url, str):
                break
            if next_url in urls:  # detect loops
                logger.warning(f"pagination loop detected at {next_url}")
                break
            urls.append(next_url)
            current_url = next_url
        except Exception as e:
            logger.warning(f"pagination follow failed: {e!r}")
            break
    
    return urls


def detect_encoding(html_bytes: bytes, content_type: str = "") -> str:
    """Detect encoding from raw bytes + Content-Type header.
    
    Priority: Content-Type charset > BOM > meta charset > chardet > utf-8
    """
    # 1. Content-Type charset
    if content_type:
        m = re.search(r'charset=([^\s;]+)', content_type, re.I)
        if m:
            return m.group(1).strip('"\'')
    
    # 2. BOM detection
    if html_bytes[:3] == b'\xef\xbb\xbf':
        return 'utf-8'
    if html_bytes[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return 'utf-16'
    
    # 3. Meta charset in first 2KB
    head = html_bytes[:2048].decode('ascii', errors='ignore')
    m = re.search(r'<meta[^>]+charset=["\']?([^\s"\'/>]+)', head, re.I)
    if m:
        return m.group(1)
    
    # 4. Try chardet
    try:
        import chardet
        result = chardet.detect(html_bytes[:4096])
        if result and result['confidence'] > 0.7:
            return result['encoding']
    except ImportError:
        pass
    
    return 'utf-8'


def resolve_redirect_url(url: str, base_url: str = "") -> str:
    """Resolve a possibly-relative URL against a base URL."""
    if not url:
        return ""
    if url.startswith(("http://", "https://", "//")):
        if url.startswith("//"):
            return "https:" + url
        return url
    if url.startswith("/"):
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{url}"
    if base_url:
        from urllib.parse import urljoin
        return urljoin(base_url, url)
    return url
