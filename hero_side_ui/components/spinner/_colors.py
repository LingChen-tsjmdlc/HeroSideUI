"""Spinner 颜色解析。"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS


VALID_VARIANTS = ("default", "simple", "gradient", "spinner", "wave", "dots")
VALID_COLORS = (
    "default", "primary", "secondary", "success", "warning", "danger",
)
VALID_SIZES = ("sm", "md", "lg", "small", "medium", "large")


def resolve_indicator_color(name: str, theme: str) -> QColor:
    """spinner 的主色（圆弧/dot/bar 的 bg-{color}），label 也用同色。

    HeroUI 规则:
        - default: zinc-400（中性灰，亮暗都看得见）
        - 其他:    {color}-500
    """
    if name == "default":
        # default 在亮模式偏亮、暗模式偏深，避免和背景同色看不见
        return QColor(HEROUI_COLORS["default"][500 if theme == "light" else 400])
    palette = HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])
    return QColor(palette[500])


__all__ = [
    "VALID_VARIANTS",
    "VALID_COLORS",
    "VALID_SIZES",
    "resolve_indicator_color",
]
