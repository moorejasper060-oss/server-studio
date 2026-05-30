# src/server_studio/ui/theme.py
from __future__ import annotations

DEFAULT_THEME = "grass-green"

# Shared dark base tokens (same across all themes).
BASE = {
    "bg": "#0a0e0b",
    "panel": "#0f1511",
    "panel2": "#121a14",
    "line": "#1f2a22",
    "text": "#e8efe9",
    "muted": "#8b988f",
}

THEMES: dict[str, dict] = {
    "grass-green": {"label": "Grass Green", "accent": "#39d353", "accent_dim": "#143020",
                    "accent_border": "#1f5233", "accent_text": "#bfe9c8", "glow": "#39d353"},
    "diamond-blue": {"label": "Diamond Blue", "accent": "#4aa8ff", "accent_dim": "#102132",
                     "accent_border": "#1f4a7a", "accent_text": "#9cc2ff", "glow": "#4aa8ff"},
    "emerald-teal": {"label": "Emerald Teal", "accent": "#2bd4c0", "accent_dim": "#0f2a26",
                     "accent_border": "#1f5249", "accent_text": "#9fe6da", "glow": "#2bd4c0"},
    "nether-amber": {"label": "Nether Amber", "accent": "#ff8a3d", "accent_dim": "#321d10",
                     "accent_border": "#7a4422", "accent_text": "#ffc79c", "glow": "#ff8a3d"},
    "amethyst": {"label": "Amethyst", "accent": "#a371f7", "accent_dim": "#221a3a",
                 "accent_border": "#4a3a7a", "accent_text": "#cdb6ff", "glow": "#a371f7"},
    "redstone": {"label": "Redstone", "accent": "#ff5a52", "accent_dim": "#321214",
                 "accent_border": "#7a2a2c", "accent_text": "#ffb0ac", "glow": "#ff5a52"},
}

THEME_ORDER = list(THEMES)


def qss(theme_key: str) -> str:
    """Return the full Qt stylesheet for a theme (falls back to default if unknown)."""
    t = THEMES.get(theme_key) or THEMES[DEFAULT_THEME]
    c = {**BASE, **t}
    return f"""
    QWidget {{ background: {c['bg']}; color: {c['text']};
               font-family: 'Segoe UI', sans-serif; font-size: 14px; }}
    QFrame#Panel {{ background: {c['panel']}; border: 1px solid {c['line']};
                    border-radius: 14px; }}
    QLabel#Muted {{ color: {c['muted']}; }}
    QLabel#Badge {{ color: {c['accent_text']}; background: {c['accent_dim']};
                    border: 1px solid {c['accent_border']}; border-radius: 11px;
                    padding: 2px 9px; }}
    QPushButton {{ background: {c['panel2']}; color: {c['text']};
                   border: 1px solid {c['line']}; border-radius: 9px; padding: 8px 14px; }}
    QPushButton#Accent {{ background: {c['accent']}; color: {c['bg']};
                          border: none; font-weight: 700; }}
    QPushButton#AccentGhost {{ background: {c['accent_dim']}; color: {c['accent']};
                               border: 1px solid {c['accent_border']}; }}
    QPlainTextEdit#Console {{ background: #070a08; border: 1px solid #16201a;
                              border-radius: 10px; font-family: Consolas, monospace;
                              font-size: 12px; }}
    """
