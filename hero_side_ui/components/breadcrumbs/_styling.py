"""Breadcrumbs 配色 token：非 current 50%、current 全色、分隔 default-400。"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS


def _qcolor(hex_color: str, alpha: float = 1.0) -> QColor:
    """把十六进制色转成带透明度的 QColor。

    Args:
        hex_color: 十六进制颜色字符串。
        alpha: 透明度，默认 1.0 不透明。

    Returns:
        已设置 alphaF 的 QColor。
    """
    c = QColor(hex_color)
    c.setAlphaF(alpha)
    return c


def _foreground(theme: str) -> str:
    """官方 foreground 色（default-foreground 语义）。

    Args:
        theme: 主题名。

    Returns:
        暗色 #ffffff，亮色 #000000。
    """
    return "#ffffff" if theme == "dark" else "#000000"


def color_base(color: str, theme: str) -> str:
    """语义色 100% 基色。

    Args:
        color: 语义色名或 foreground；未命中回退 primary。
        theme: 主题名。

    Returns:
        current 项文字与 hover 提亮的基准色。
    """
    if color == "foreground":
        return _foreground(theme)
    return HEROUI_COLORS.get(color, HEROUI_COLORS["primary"])[500]


def build_item_styles(color: str, theme: str, is_current: bool) -> dict:
    """返回单项配色 token。

    Args:
        color: 语义色名或 foreground。
        theme: 主题名。
        is_current: 是否为当前项。

    Returns:
        含 text / text_hover / text_pressed / separator 的 dict；
        非 current 时 foreground 按 50%、语义色按 80% 降透明度。
    """
    base = color_base(color, theme)
    # 官方：foreground 用 /50，语义色用 /80；current 全色
    alpha = 1.0 if is_current else (0.5 if color == "foreground" else 0.8)
    return {
        "text": _qcolor(base, alpha),
        "text_hover": _qcolor(base, 1.0),
        "text_pressed": _qcolor(base, 0.5),
        "separator": _qcolor(base, alpha),
    }


def build_list_styles(variant: str, theme: str) -> dict:
    """列表容器配色：solid 底色 / bordered 边框 / light 无。

    Args:
        variant: solid / bordered / light。
        theme: 主题名。

    Returns:
        含 bg / border / border_w 的 dict。

    Note:
        暗色下浅阶索引镜像反转（100↔800 / 200↔700），保证视觉亮度对应。
    """
    is_dark = theme == "dark"
    d = HEROUI_COLORS["default"]

    def shade(shade: int) -> str:
        if not is_dark:
            return d[shade]
        return d[
            (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)[
                9 - (50, 100, 200, 300, 400, 500, 600, 700, 800, 900).index(shade)
            ]
        ]

    if variant == "solid":
        return {"bg": _qcolor(shade(100)), "border": "none", "border_w": 0}
    if variant == "bordered":
        return {"bg": "none", "border": _qcolor(shade(200)), "border_w": 2}
    return {"bg": "none", "border": "none", "border_w": 0}


def separator_color(theme: str) -> str:
    """列表级分隔符默认色。

    Args:
        theme: 主题名（当前实现不区分主题，保持与 default-400 一致）。

    Returns:
        text-default-400 的十六进制色。
    """
    return HEROUI_COLORS["default"][400]
