"""Alert color tokens for 4 variants × 6 colors × 2 themes.

色阶映射严格对照 HeroUI alert.ts：
- solid:  纯色背景
- flat:   彩色浅底 + 无边框
- bordered: 透明底 + 彩色边框
- faded:  flat 背景 + bordered 边框 (= flat + bordered)
"""

from __future__ import annotations

from ...themes import HEROUI_COLORS, RADIUS
from ...utils import hex_to_rgba


def build_alert_styles(
    variant: str, color: str, theme: str, radius: str,
) -> dict:
    """Return color tokens for all sub-elements.

    Keys: base_bg, base_fg, base_border, icon_wrapper_bg, icon_color,
          title_color, desc_color, close_btn_color
    """
    is_dark = theme == "dark"
    c = HEROUI_COLORS.get(color, HEROUI_COLORS["primary"])
    d = HEROUI_COLORS["default"]

    if variant == "solid":
        return _solid(c, d, is_dark, color)
    if variant == "bordered":
        return _bordered(c, d, is_dark, color)
    if variant == "faded":
        return _faded(c, d, is_dark, color)
    return _flat(c, d, is_dark, color)


def _fg_on_solid(color_name: str, is_dark: bool) -> str:
    if color_name == "warning":
        return "#000000"
    if color_name == "default":
        return "#d4d4d8" if is_dark else "#ffffff"
    return "#ffffff"


# ---- solid ----

def _solid(c: dict, d: dict, is_dark: bool, color_name: str) -> dict:
    if color_name == "default":
        bg = d[700] if is_dark else d[500]
    else:
        bg = c[500]
    fg = _fg_on_solid(color_name, is_dark)
    return {
        "base_bg": bg, "base_fg": fg, "base_border": "none",
        "icon_wrapper_bg": "transparent", "icon_color": fg,
        "title_color": fg, "desc_color": hex_to_rgba(fg, 0.85),
        "close_btn_color": fg,
    }


# ---- flat ----

def _flat(c: dict, d: dict, is_dark: bool, color_name: str) -> dict:
    if color_name == "default":
        bg = d[100] if not is_dark else hex_to_rgba(d[500], 0.15)
        fg = d[800] if not is_dark else d[100]
        iwr = d[50] if not is_dark else hex_to_rgba(d[200], 0.15)
        ic = d[700] if not is_dark else d[300]
        dc = d[600] if not is_dark else d[400]
        cb = d[400]
    else:
        bg = c[50] if not is_dark else hex_to_rgba(c[500], 0.2)
        fg = c[600] if not is_dark else c[200]
        iwr = c[100] if not is_dark else hex_to_rgba(c[200], 0.2)
        ic = c[500] if not is_dark else c[400]
        dc = c[500] if not is_dark else c[300]
        cb = c[500] if not is_dark else c[400]
    return {
        "base_bg": bg, "base_fg": fg, "base_border": "none",
        "icon_wrapper_bg": iwr, "icon_color": ic,
        "title_color": fg, "desc_color": dc,
        "close_btn_color": cb,
    }


# ---- bordered ----
# 边框较粗(2px)、颜色较深，与 faded 的浅细边框形成对比

def _bordered(c: dict, d: dict, is_dark: bool, color_name: str) -> dict:
    if color_name == "default":
        bd = d[300] if not is_dark else d[600]
        fg = d[800] if not is_dark else d[100]
        iwr = d[200] if not is_dark else d[100]
        ic = d[700] if not is_dark else d[300]
        dc = d[600] if not is_dark else d[400]
        cb = d[400]
    else:
        bd = c[300] if not is_dark else c[600]
        fg = c[600] if not is_dark else c[200]
        iwr = c[100] if not is_dark else hex_to_rgba(c[100], 0.15)
        ic = c[500] if not is_dark else c[400]
        dc = c[500] if not is_dark else c[300]
        cb = c[500] if not is_dark else c[400]
    return {
        "base_bg": "transparent", "base_fg": fg,
        "base_border": f"2px solid {bd}",
        "icon_wrapper_bg": iwr, "icon_color": ic,
        "title_color": fg, "desc_color": dc,
        "close_btn_color": cb,
    }


# ---- faded = flat 背景 + 浅色细边框 ----
# 边框较细(1px)、颜色较浅，与 bordered 形成对比

def _faded(c: dict, d: dict, is_dark: bool, color_name: str) -> dict:
    flat_tokens = _flat(c, d, is_dark, color_name)
    if color_name == "default":
        bd = d[200] if not is_dark else d[700]
    else:
        bd = c[200] if not is_dark else c[700]
    return {
        **flat_tokens,
        "base_border": f"1px solid {bd}",
    }
