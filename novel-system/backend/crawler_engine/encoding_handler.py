"""Encoding handler (v160) — auto-detect and convert page encoding to UTF-8."""
import re


def detect_and_decode(raw_bytes: bytes, content_type: str = "") -> str:
    """Detect encoding and decode to UTF-8 string.
    
    Priority: Content-Type charset > BOM > meta charset > statistical detection > utf-8
    """
    if not raw_bytes:
        return ""
    
    # 1. Content-Type charset
    if content_type:
        m = re.search(r'charset=([^\s;]+)', content_type, re.I)
        if m:
            enc = m.group(1).strip('"\'')
            try:
                return raw_bytes.decode(enc, errors="replace")
            except (LookupError, TypeError):
                pass
    
    # 2. BOM detection
    if raw_bytes[:3] == b'\xef\xbb\xbf':
        return raw_bytes[3:].decode("utf-8", errors="replace")
    if raw_bytes[:2] == b'\xff\xfe':
        return raw_bytes.decode("utf-16-le", errors="replace")
    if raw_bytes[:2] == b'\xfe\xff':
        return raw_bytes.decode("utf-16-be", errors="replace")
    
    # 3. Meta charset in first 2KB
    head = raw_bytes[:2048].decode("ascii", errors="ignore")
    m = re.search(r'<meta[^>]+charset=["\']?([^\s"\'/>]+)', head, re.I)
    if m:
        enc = m.group(1)
        try:
            return raw_bytes.decode(enc, errors="replace")
        except (LookupError, TypeError):
            pass
    
    # 4. Try common Chinese encodings
    for enc in ("utf-8", "gbk", "gb2312", "gb18030", "big5"):
        try:
            decoded = raw_bytes.decode(enc, errors="strict")
            # Check for replacement chars — if too many, encoding is wrong
            if decoded.count("\ufffd") < len(decoded) * 0.01:
                return decoded
        except (UnicodeDecodeError, LookupError):
            continue
    
    # 5. Fallback
    return raw_bytes.decode("utf-8", errors="replace")
