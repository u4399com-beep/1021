"""Smart delay strategy (v205) — randomized delays between requests."""
import random


def calculate_delay(url, tier, error_count=0, base_min=1.0, base_max=3.0):
    """Calculate delay before next request based on context.
    
    Args:
        url: target URL (unused for now, reserved for domain-based delays)
        tier: which fetch tier (httpx is fast, playwright is slow)
        error_count: recent error count (more errors = longer delay)
        base_min: minimum delay
        base_max: maximum delay
    
    Returns: delay in seconds (float)
    """
    # Tier-based adjustment
    if tier == "playwright":
        base_min += 1.0
        base_max += 2.0
    elif tier == "browser-use":
        base_min += 2.0
        base_max += 5.0
    
    # Error-based backoff
    if error_count > 0:
        multiplier = 1.0 + (error_count * 0.5)
        base_min *= multiplier
        base_max *= multiplier
    
    # Cap at 60s
    base_min = min(base_min, 30.0)
    base_max = min(base_max, 60.0)
    
    # Log-normal distribution for realistic timing
    delay = random.uniform(base_min, base_max)
    return round(delay, 2)
