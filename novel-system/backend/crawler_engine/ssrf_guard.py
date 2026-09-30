"""SSRF protection — block private/loopback/link-local addresses."""

import ipaddress
from urllib.parse import urlparse

# Blocked IP ranges
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local (cloud metadata)
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("::1/128"),         # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),        # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),       # IPv6 link-local
]

# Allowed schemes
_ALLOWED_SCHEMES = {"http", "https"}


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to fetch (not pointing to private/metadata endpoints)."""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    # Block known metadata endpoints
    if hostname in ("metadata.google.internal", "169.254.169.254", "metadata"):
        return False
    # Try to resolve as IP
    try:
        ip = ipaddress.ip_address(hostname)
        for net in _PRIVATE_NETWORKS:
            if ip in net:
                return False
    except ValueError:
        pass  # hostname is a domain, not IP — allow (DNS resolution check happens at fetch time)
    return True


def validate_url_or_raise(url: str) -> str:
    """Validate URL for SSRF safety. Returns the URL if safe, raises ValueError otherwise."""
    if not is_safe_url(url):
        raise ValueError(f"URL blocked by SSRF protection: {url}")
    return url
