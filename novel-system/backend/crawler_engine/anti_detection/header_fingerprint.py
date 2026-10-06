"""Deep header fingerprint randomization (v147).

Generates realistic browser header sets that vary per request,
including Sec-Ch-Ua, Accept, Accept-Encoding variations.
"""
import random


# Real browser header templates
BROWSER_TEMPLATES = [
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Not)A;Brand";v="99", "Chromium";v="127"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"Windows"',
    },
    {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Not)A;Brand";v="99", "Chromium";v="127"',
        "sec_ch_ua_mobile": "?0",
        "sec_ch_ua_platform": '"macOS"',
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "sec_ch_ua": None,  # Firefox doesn't send Sec-Ch-Ua
        "sec_ch_ua_mobile": None,
        "sec_ch_ua_platform": None,
    },
    {
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "sec_ch_ua": '"Not)A;Brand";v="99", "Chromium";v="127"',
        "sec_ch_ua_mobile": "?1",
        "sec_ch_ua_platform": '"iOS"',
    },
]

ACCEPT_VARIATIONS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
]

ACCEPT_LANG_VARIATIONS = [
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4",
    "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
]

ACCEPT_ENCODING_VARIATIONS = [
    "gzip, deflate, br",
    "gzip, deflate",
    "br, gzip, deflate",
    "gzip, deflate, br, zstd",
]


def generate_fingerprint_headers() -> dict[str, str]:
    """Generate a complete set of randomized but realistic browser headers."""
    template = random.choice(BROWSER_TEMPLATES)
    headers = {
        "User-Agent": template["user_agent"],
        "Accept": random.choice(ACCEPT_VARIATIONS),
        "Accept-Language": random.choice(ACCEPT_LANG_VARIATIONS),
        "Accept-Encoding": random.choice(ACCEPT_ENCODING_VARIATIONS),
        "Connection": random.choice(["keep-alive", "close"]),
        "Cache-Control": random.choice(["no-cache", "max-age=0", "no-cache, no-store"]),
    }
    # Add Sec-Ch-Ua headers only for Chromium-based browsers
    if template["sec_ch_ua"]:
        headers["Sec-Ch-Ua"] = template["sec_ch_ua"]
        headers["Sec-Ch-Ua-Mobile"] = template["sec_ch_ua_mobile"]
        headers["Sec-Ch-Ua-Platform"] = template["sec_ch_ua_platform"]
        headers["Sec-Fetch-Dest"] = "document"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Site"] = random.choice(["none", "same-origin", "cross-site"])
        headers["Sec-Fetch-User"] = "?1"
        headers["Upgrade-Insecure-Requests"] = "1"
    return headers


# HTTP/2 support flag (randomized)
def should_use_http2():
    """Randomly enable HTTP/2 to avoid fingerprinting."""
    import random
    return random.random() < 0.5


# Common Referer values to simulate natural browsing
REFERER_VALUES = [
    None,  # Direct visit (no Referer)
    'https://www.google.com/',
    'https://www.baidu.com/',
    'https://www.bing.com/',
    'https://www.sogou.com/',
    'https://www.google.com/search?q=novel',
    'https://www.baidu.com/s?wd=novel',
]

def get_random_referer():
    """Return a random Referer value (or None for direct visit)."""
    import random
    return random.choice(REFERER_VALUES)


# DNT (Do Not Track) randomization
def get_random_dnt():
    """Randomly set DNT header to 0, 1, or omit."""
    import random
    return random.choice(['0', '1', None])


# Sec-Fetch-Site randomization (simulate different navigation sources)
SEC_FETCH_SITE_VALUES = ['none', 'same-origin', 'same-site', 'cross-site']

def get_random_sec_fetch_site():
    import random
    return random.choice(SEC_FETCH_SITE_VALUES)


# X-Forwarded-For randomization (simulate requests through proxies)
def get_random_xff():
    """Generate a random X-Forwarded-For chain to simulate proxy hops."""
    import random
    # Sometimes omit, sometimes include 1-2 fake IPs
    if random.random() < 0.3:
        return None  # Direct request
    ip1 = f'{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}'
    if random.random() < 0.3:
        ip2 = f'{random.randint(10,192)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}'
        return f'{ip1}, {ip2}'
    return ip1


# Request timeout randomization
def get_random_timeout(base=30, jitter=10):
    """Randomize timeout to avoid fingerprinting by consistent timeout patterns."""
    import random
    return base + random.randint(0, jitter)


# Header order randomization (v298) — reorder dict keys for httpx
HEADER_ORDERS_V2 = [
    ["User-Agent", "Accept", "Accept-Language", "Accept-Encoding", "Connection"],
    ["Accept", "Accept-Language", "User-Agent", "Accept-Encoding", "Connection"],
    ["Accept-Encoding", "Accept", "User-Agent", "Accept-Language", "Connection"],
    ["Connection", "User-Agent", "Accept", "Accept-Encoding", "Accept-Language"],
]

def reorder_headers(headers: dict) -> dict:
    """Reorder headers dict based on random browser-like order."""
    import random
    order = random.choice(HEADER_ORDERS_V2)
    result = {}
    for key in order:
        for k, v in headers.items():
            if k == key:
                result[k] = v
                break
    # Add remaining
    for k, v in headers.items():
        if k not in order:
            result[k] = v
    return result
