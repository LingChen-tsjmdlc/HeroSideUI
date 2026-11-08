"""Avatar 配色 token（6 色 × 2 主题），fallback 走 solid 同 Chip。"""

from __future__ import annotations

from ...themes import HEROUI_COLORS


def _fg_on_solid(color_name: str, is_dark: bool) -> str:
    """求 solid 底上的前景色（文字 / 图标）。

    Args:
        color_name: 语义色名；warning 底色过亮需用黑字。
        is_dark: 是否深色主题，仅影响 default 分支。

    Returns:
        十六进制前景色字符串。
    """
    if color_name == "warning":
        return "#000000"
    if color_name == "default":
        return "#d4d4d8" if is_dark else "#ffffff"
    return "#ffffff"


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
    offset = "#000000" if is_dark else "#ffffff"

    return {
        "bg": bg,
        "fg": fg,
        "ring_color": ring,
        "offset_color": offset,
    }
