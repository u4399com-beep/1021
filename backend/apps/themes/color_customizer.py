"""Theme color customization (v96)."""
from __future__ import annotations

COLOR_SCHEMES = {
    "uaa_blue":    {"primary": "#1e88e5", "bg": "#f5f9ff", "text": "#2c3e50"},
    "classic_red":  {"primary": "#c62828", "bg": "#faf5f5", "text": "#333"},
    "forest_green": {"primary": "#2e7d32", "bg": "#f5faf5", "text": "#333"},
    "royal_purple": {"primary": "#6a1b9a", "bg": "#faf5fb", "text": "#333"},
    "sunset_orange": {"primary": "#ef6c00", "bg": "#fff8f0", "text": "#333"},
    "ocean_teal":  {"primary": "#00838f", "bg": "#f0fafb", "text": "#333"},
    "graphite_gray": {"primary": "#455a64", "bg": "#f5f5f5", "text": "#333"},
}

def get_scheme(name: str) -> dict:
    return COLOR_SCHEMES.get(name, COLOR_SCHEMES["uaa_blue"])

def list_schemes() -> list[dict]:
    return [{"key": k, "name": k.replace("_", " ").title(), **v} for k, v in COLOR_SCHEMES.items()]

def generate_css(scheme_name: str) -> str:
    s = get_scheme(scheme_name)
    return f""":root {{
  --primary: {s['primary']};
  --bg: {s['bg']};
  --text: {s['text']};
}}"""
