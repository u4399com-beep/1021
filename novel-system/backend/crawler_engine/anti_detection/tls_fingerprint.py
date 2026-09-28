"""TLS fingerprint + header order randomization (v135)."""
import random
from typing import Any


# TLS cipher suites in random order to avoid fingerprinting
TLS_CIPHER_SUITES = [
    "TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_AES_128_GCM_SHA256", "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES256-GCM-SHA384", "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-CHACHA20-POLY1305", "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES128-GCM-SHA256",
]

# Common header orders — real browsers send headers in consistent but varied order
HEADER_ORDERS = [
    ["accept", "accept-encoding", "accept-language", "connection", "host", "user-agent"],
    ["host", "connection", "accept", "user-agent", "accept-encoding", "accept-language"],
    ["accept-encoding", "accept", "accept-language", "user-agent", "connection", "host"],
    ["user-agent", "accept", "accept-language", "accept-encoding", "connection", "host"],
]


def get_random_tls_ciphers() -> list[str]:
    """Return cipher suites in a randomized order."""
    suites = TLS_CIPHER_SUITES.copy()
    random.shuffle(suites)
    return suites[:5]  # Use 5 random ciphers


def get_random_header_order() -> list[str]:
    """Return a random header order to mimic different browser variants."""
    return random.choice(HEADER_ORDERS)


def build_randomized_headers(base_headers: dict[str, str]) -> dict[str, str]:
    """Reorder headers based on a random browser-like order."""
    order = get_random_header_order()
    result = {}
    for h in order:
        # Case-insensitive match
        for k, v in base_headers.items():
            if k.lower() == h:
                result[k] = v
                break
    # Add any remaining headers not in the order list
    for k, v in base_headers.items():
        if k.lower() not in [h.lower() for h in order]:
            result[k] = v
    return result
