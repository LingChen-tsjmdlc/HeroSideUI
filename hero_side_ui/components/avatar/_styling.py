"""Avatar 配色 token（6 语义色 × 2 主题）。

对照 HeroUI avatar.ts：
- fallback 背景走 colorVariants.solid（同 Chip solid：纯色底 + 对比字），
  default 底在暗色下用 default[700]、亮色用 default[500]。
- text-white / warning 用黑字。
- isBordered: ring-{color} 描边色（default 用 default 语义色），
  ring-offset 用背景色（页面底色）隔出一圈缝隙。
"""

from __future__ import annotations

from ...themes import HEROUI_COLORS


def _fg_on_solid(color_name: str, is_dark: bool) -> str:
    """solid 底上的前景色（文字 / 图标）。"""
    if color_name == "warning":
        return "#000000"
    if color_name == "default":
        return "#d4d4d8" if is_dark else "#ffffff"
    return "#ffffff"


def build_avatar_styles(color: str, theme: str) -> dict:
    """返回 Avatar 各元素配色。

    Keys: bg, fg, ring_color, offset_color
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
