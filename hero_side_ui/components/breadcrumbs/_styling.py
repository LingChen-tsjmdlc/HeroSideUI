"""Breadcrumbs 配色 token。

对照 HeroUI breadcrumbs.ts + breadcrumbItem.ts：
- item 非 current：text-foreground/50（语义色 80%）；current：全色
- separator：列表级 text-default-400，item 级跟随 color 同透明度
- variant solid：bg-default-100；bordered：border 2px default-200；light：无
"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS


def _qcolor(hex_color: str, alpha: float = 1.0) -> QColor:
    c = QColor(hex_color)
    c.setAlphaF(alpha)
    return c


def _foreground(theme: str) -> str:
    """官方 foreground 色（default-foreground 语义）：亮黑暗白。"""
    return "#ffffff" if theme == "dark" else "#000000"


def color_base(color: str, theme: str) -> str:
    """语义色 100% 基色（current 项文字 / hover 提亮目标）。"""
    if color == "foreground":
        return _foreground(theme)
    return HEROUI_COLORS.get(color, HEROUI_COLORS["primary"])[500]


def build_item_styles(color: str, theme: str, is_current: bool) -> dict:
    """单项配色（QColor 对象）。

    Keys: text（常态）、text_hover（hover 提亮到全色）、text_pressed（50%）、
    separator（跟随 color 同透明度）
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

    暗色下浅阶索引镜像反转（100↔800 / 200↔700）。
    """
    is_dark = theme == "dark"
    d = HEROUI_COLORS["default"]

    def shade(shade: int) -> str:
        if not is_dark:
            return d[shade]
        return d[(50, 100, 200, 300, 400, 500, 600, 700, 800, 900)[
            9 - (50, 100, 200, 300, 400, 500, 600, 700, 800, 900).index(shade)
        ]]

    if variant == "solid":
        return {"bg": _qcolor(shade(100)), "border": "none", "border_w": 0}
    if variant == "bordered":
        return {"bg": "none", "border": _qcolor(shade(200)), "border_w": 2}
    return {"bg": "none", "border": "none", "border_w": 0}


def separator_color(theme: str) -> str:
    """列表级分隔符默认色：text-default-400。"""
    return HEROUI_COLORS["default"][400]
