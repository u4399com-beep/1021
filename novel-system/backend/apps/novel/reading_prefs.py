"""Reading experience preferences (v78) — font, background, night mode."""


THEMES = {
    "default": {"bg": "#ffffff", "text": "#2c3e50", "font": "'Noto Serif SC', serif", "size": 18, "line_height": 2.0},
    "sepia": {"bg": "#f4ecd8", "text": "#5b4636", "font": "'Noto Serif SC', serif", "size": 18, "line_height": 2.0},
    "night": {"bg": "#1a1a1a", "text": "#cccccc", "font": "'Noto Sans SC', sans-serif", "size": 18, "line_height": 2.0},
    "green": {"bg": "#c7edcc", "text": "#333333", "font": "'Noto Serif SC', serif", "size": 18, "line_height": 2.0},
    "high_contrast": {"bg": "#000000", "text": "#ffff00", "font": "'Noto Sans SC', sans-serif", "size": 20, "line_height": 2.2},
}


def get_theme(name: str = "default") -> dict:
    return THEMES.get(name, THEMES["default"])


def list_themes() -> list[dict]:
    return [{"key": k, "name": n, **v} for k, v in {
        "default": {"name": "白天"},
        "sepia": {"name": "护眼黄"},
        "night": {"name": "夜间"},
        "green": {"name": "护眼绿"},
        "high_contrast": {"name": "高对比"},
    }.items() if k in THEMES for n in [None]]


def apply_to_html(html: str, theme_name: str = "default", font_size: int = 0) -> str:
    """Wrap content with reading theme CSS."""
    theme = get_theme(theme_name)
    size = font_size or theme["size"]
    css = f"""
    <style>
    .reading-content {{
        background: {theme['bg']}; color: {theme['text']};
        font-family: {theme['font']}; font-size: {size}px;
        line-height: {theme['line_height']}; padding: 24px;
    }}
    .reading-content p {{ text-indent: 2em; margin-bottom: 16px; }}
    </style>
    <div class="reading-content">{html}</div>
    """
    return css
