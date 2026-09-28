"""Human behavior simulation (v137) — mouse moves, scrolls, delays."""
import random
import time
from typing import Any


def simulate_human_delay(min_s: float = 1.0, max_s: float = 3.0) -> float:
    """Random delay that mimics human reading/thinking time."""
    # Use a log-normal distribution for more realistic timing
    delay = random.lognormvariate(0.5, 0.3)
    return max(min_s, min(max_s, delay))


def simulate_mouse_move(page) -> None:
    """Move mouse to random positions to appear human."""
    try:
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1200)
            y = random.randint(100, 600)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.5))
    except Exception:
        pass


def simulate_scroll(page, direction: str = "down") -> None:
    """Simulate human-like scrolling."""
    try:
        steps = random.randint(3, 8)
        for i in range(steps):
            scroll_y = (i + 1) * random.randint(100, 400)
            if direction == "down":
                page.evaluate(f"window.scrollTo(0, {scroll_y})")
            else:
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight - {scroll_y})")
            time.sleep(random.uniform(0.3, 1.0))
    except Exception:
        pass


def simulate_reading(page, duration_s: float = 2.0) -> None:
    """Simulate reading a page — pause + occasional scroll."""
    time.sleep(simulate_human_delay(0.5, duration_s))
    if random.random() < 0.3:
        simulate_scroll(page)


def full_human_simulation(page) -> None:
    """Full human behavior simulation — call after page load."""
    simulate_mouse_move(page)
    if random.random() < 0.7:
        simulate_scroll(page)
    simulate_reading(page, duration_s=random.uniform(1.0, 3.0))
