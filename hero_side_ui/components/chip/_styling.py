"""Chip color tokens for 7 variants × 6 colors × 2 themes.

色阶映射对照 HeroUI chip.ts（复用 colorVariants）：
- solid:    纯色背景 + 对比色文字
- bordered: 透明底 + 彩色边框
- light:    透明底 + 彩色文字，无边框
- flat:     彩色浅底 + 无边框
- faded:    flat 背景 + 浅色细边框
- shadow:   solid 背景 + 彩色投影
- dot:      透明底 + default 细边框 + foreground 文字 + 彩色小圆点
"""

from __future__ import annotations

from ...themes import HEROUI_COLORS
from ...utils import hex_to_rgba


def build_chip_styles(variant: str, color: str, theme: str) -> dict:
    """返回 Chip 各子元素的配色 token。

    Keys: bg, fg, border, close_color, dot_color, shadow_color, has_shadow
    """
    is_dark = theme == "dark"
    c = HEROUI_COLORS.get(color, HEROUI_COLORS["primary"])
    d = HEROUI_COLORS["default"]

    if variant == "bordered":
        return _bordered(c, d, is_dark, color)
    if variant == "light":
        return _light(c, d, is_dark, color)
    if variant == "flat":
        return _flat(c, d, is_dark, color)
    if variant == "faded":
        return _faded(c, d, is_dark, color)
    if variant == "shadow":
        return _shadow(c, d, is_dark, color)
    if variant == "dot":
        return _dot(c, d, is_dark, color)
    return _solid(c, d, is_dark, color)


def _fg_on_solid(color_name: str, is_dark: bool) -> str:
    """solid/shadow 背景上的文字色。"""
    if color_name == "warning":
        return "#000000"
    if color_name == "default":
        return "#d4d4d8" if is_dark else "#ffffff"
    return "#ffffff"


def _base_token(bg, fg, border, dot_color, shadow_color=None, has_shadow=False) -> dict:
    return {
        "bg": bg,
        "fg": fg,
        "border": border,
        "close_color": fg,
        "dot_color": dot_color,
        "shadow_color": shadow_color,
        "has_shadow": has_shadow,
    }


# ---- solid ----

def _solid(c, d, is_dark, color_name) -> dict:
    bg = (d[700] if is_dark else d[500]) if color_name == "default" else c[500]
    fg = _fg_on_solid(color_name, is_dark)
    return _base_token(bg, fg, "none", c[500])


# ---- shadow = solid + 彩色投影 ----

def _shadow(c, d, is_dark, color_name) -> dict:
    tok = _solid(c, d, is_dark, color_name)
    tok["has_shadow"] = True
    tok["shadow_color"] = d[400] if color_name == "default" else c[500]
    return tok


# ---- flat ----

def _flat(c, d, is_dark, color_name) -> dict:
    if color_name == "default":
        bg = d[100] if not is_dark else hex_to_rgba(d[500], 0.15)
        fg = d[700] if not is_dark else d[200]
    else:
        bg = c[50] if not is_dark else hex_to_rgba(c[500], 0.2)
        fg = c[600] if not is_dark else c[300]
    return _base_token(bg, fg, "none", c[500])


# ---- bordered ----

def _bordered(c, d, is_dark, color_name) -> dict:
    if color_name == "default":
        bd = d[300] if not is_dark else d[600]
        fg = d[700] if not is_dark else d[200]
    else:
        bd = c[500]
        fg = c[500] if not is_dark else c[400]
    return _base_token("transparent", fg, f"2px solid {bd}", c[500])


# ---- light ----

def _light(c, d, is_dark, color_name) -> dict:
    if color_name == "default":
        fg = d[700] if not is_dark else d[200]
    else:
        fg = c[500] if not is_dark else c[400]
    return _base_token("transparent", fg, "none", c[500])


# ---- faded = flat 背景 + 浅色细边框 ----

def _faded(c, d, is_dark, color_name) -> dict:
    bg = d[100] if not is_dark else d[800]
    bd = d[300] if not is_dark else d[700]
    if color_name == "default":
        fg = d[700] if not is_dark else d[200]
    else:
        fg = c[500] if not is_dark else c[400]
    return _base_token(bg, fg, f"1px solid {bd}", c[500])


# ---- dot = 透明底 + default 细边框 + foreground 文字 + 彩色圆点 ----

def _dot(c, d, is_dark, color_name) -> dict:
    bd = d[300] if not is_dark else d[600]
    fg = d[700] if not is_dark else d[200]  # foreground 文字，不随 color 变
    dot = d[400] if color_name == "default" else c[500]
    return _base_token("transparent", fg, f"1px solid {bd}", dot)
