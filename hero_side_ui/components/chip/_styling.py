"""Chip 配色 token：7 variants × 6 colors × 2 themes，对照 HeroUI chip.ts。"""

from __future__ import annotations

from ...themes import HEROUI_COLORS
from ...utils import hex_to_rgba


def build_chip_styles(variant: str, color: str, theme: str) -> dict:
    """返回 Chip 各子元素的配色 token。

    Args:
        variant: solid / shadow / flat / bordered / light / faded / dot。
        color: 语义色名，未命中回退 primary。
        theme: 主题名，dark 走深色取值。

    Returns:
        含 bg / fg / border / close_color / dot_color /
        shadow_color / has_shadow 的 dict。
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
    """solid / shadow 背景上的文字色。

    Args:
        color_name: 语义色名；warning 底色过亮用黑字。
        is_dark: 是否深色主题，仅影响 default 分支。

    Returns:
        十六进制前景色字符串。
    """
    if color_name == "warning":
        return "#000000"
    if color_name == "default":
        return "#d4d4d8" if is_dark else "#ffffff"
    return "#ffffff"


def _base_token(bg, fg, border, dot_color, shadow_color=None, has_shadow=False) -> dict:
    """组装统一结构的配色 token。

    Args:
        bg: 背景色。
        fg: 前景文字色。
        border: 边框 QSS 片段。
        dot_color: 圆点色。
        shadow_color: 投影色；None 表示无投影。
        has_shadow: 是否需要挂投影效果。

    Returns:
        七个键固定齐全的 dict；close_color 默认复用 fg。
    """
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
    """solid 变体：实色底 + 反色前景。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题。
        color_name: 语义色名，default 走灰阶特殊分支。

    Returns:
        统一结构的配色 token。
    """
    bg = (d[700] if is_dark else d[500]) if color_name == "default" else c[500]
    fg = _fg_on_solid(color_name, is_dark)
    return _base_token(bg, fg, "none", c[500])


# ---- shadow = solid + 彩色投影 ----


def _shadow(c, d, is_dark, color_name) -> dict:
    """shadow 变体：在 solid 基础上补彩色投影。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题。
        color_name: 语义色名；default 用灰阶投影。

    Returns:
        has_shadow=True 且带 shadow_color 的 token。
    """
    tok = _solid(c, d, is_dark, color_name)
    tok["has_shadow"] = True
    tok["shadow_color"] = d[400] if color_name == "default" else c[500]
    return tok


# ---- flat ----


def _flat(c, d, is_dark, color_name) -> dict:
    """flat 变体：浅色底 + 无边框。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题；暗色用色阶 500 加透明度叠加。
        color_name: 语义色名。

    Returns:
        统一结构的配色 token。
    """
    if color_name == "default":
        bg = d[100] if not is_dark else hex_to_rgba(d[500], 0.15)
        fg = d[700] if not is_dark else d[200]
    else:
        bg = c[50] if not is_dark else hex_to_rgba(c[500], 0.2)
        fg = c[600] if not is_dark else c[300]
    return _base_token(bg, fg, "none", c[500])


# ---- bordered ----


def _bordered(c, d, is_dark, color_name) -> dict:
    """bordered 变体：透明底 + 2px 深边框。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题。
        color_name: 语义色名。

    Returns:
        border 为 2px solid 的 token。
    """
    if color_name == "default":
        bd = d[300] if not is_dark else d[600]
        fg = d[700] if not is_dark else d[200]
    else:
        bd = c[500]
        fg = c[500] if not is_dark else c[400]
    return _base_token("transparent", fg, f"2px solid {bd}", c[500])


# ---- light ----


def _light(c, d, is_dark, color_name) -> dict:
    """light 变体：完全透明底、无边框，只给文字上色。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题。
        color_name: 语义色名。

    Returns:
        统一结构的配色 token。
    """
    if color_name == "default":
        fg = d[700] if not is_dark else d[200]
    else:
        fg = c[500] if not is_dark else c[400]
    return _base_token("transparent", fg, "none", c[500])


# ---- faded = flat 背景 + 浅色细边框 ----


def _faded(c, d, is_dark, color_name) -> dict:
    """faded 变体：浅底 + 1px 细边框。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题。
        color_name: 语义色名。

    Returns:
        与 bordered 结构相同但边框更细更浅的 token。
    """
    bg = d[100] if not is_dark else d[800]
    bd = d[300] if not is_dark else d[700]
    if color_name == "default":
        fg = d[700] if not is_dark else d[200]
    else:
        fg = c[500] if not is_dark else c[400]
    return _base_token(bg, fg, f"1px solid {bd}", c[500])


# ---- dot = 透明底 + default 细边框 + foreground 文字 + 彩色圆点 ----


def _dot(c, d, is_dark, color_name) -> dict:
    """dot 变体：透明底 + default 细边框 + foreground 文字 + 彩色圆点。

    Args:
        c: 语义色阶字典。
        d: default 色阶字典。
        is_dark: 是否深色主题。
        color_name: 语义色名；default 用灰点，其余用主色 500。

    Returns:
        统一结构的配色 token；文字不随 color 变。
    """
    bd = d[300] if not is_dark else d[600]
    fg = d[700] if not is_dark else d[200]  # foreground 文字，不随 color 变
    dot = d[400] if color_name == "default" else c[500]
    return _base_token("transparent", fg, f"1px solid {bd}", dot)
