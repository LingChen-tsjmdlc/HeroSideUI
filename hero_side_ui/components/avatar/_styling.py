"""Avatar 配色 token（6 色 × 2 主题），fallback 走 solid 同 Chip。"""

from __future__ import annotations

from ...themes import HEROUI_COLORS
from ...themes.theme_values import get_background, get_color_foreground


def _fg_on_solid(color_name: str, is_dark: bool) -> str:
    """求 solid 底上的前景色（文字 / 图标）。

    Args:
        color_name: 语义色名。
        is_dark: 是否深色主题。

    Returns:
        十六进制前景色字符串。
    """
    return get_color_foreground(color_name, "dark" if is_dark else "light")


def build_avatar_styles(color: str, theme: str) -> dict:
    """返回 Avatar 各元素配色 token。

    Args:
        color: 语义色名，未命中时回退 default。
        theme: 主题名，dark 走深色取值。

    Returns:
        含 bg / fg / ring_color / offset_color 的 dict；
        offset 与页面背景同色，制造描边与头像之间的缝隙。
    """
    is_dark = theme == "dark"
    c = HEROUI_COLORS.get(color, HEROUI_COLORS["default"])
    d = HEROUI_COLORS["default"]

    if color == "default":
        bg = d[700] if is_dark else d[500]
        ring = d[500]
    else:
        bg = c[500]
        ring = c[500]

    fg = _fg_on_solid(color, is_dark)
    # ring-offset：与页面背景同色，制造描边与头像之间的缝隙。
    offset = get_background(theme)

    return {
        "bg": bg,
        "fg": fg,
        "ring_color": ring,
        "offset_color": offset,
    }
