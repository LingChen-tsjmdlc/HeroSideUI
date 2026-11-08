"""Spinner 颜色解析。"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS

VALID_VARIANTS = ("default", "simple", "gradient", "spinner", "wave", "dots")
VALID_COLORS = (
    "default",
    "primary",
    "secondary",
    "success",
    "warning",
    "danger",
)
VALID_SIZES = ("sm", "md", "lg", "small", "medium", "large")


def resolve_indicator_color(name: str, theme: str) -> QColor:
    """取 spinner 主色：default 用 zinc-400，其余 {color}-500；label 同色。

    Args:
        name: 颜色名；default 走专用分支，其余按调色板键查找。
        theme: 亮/暗主题名，仅影响 default 分支。

    Returns:
        对应的 Qt 颜色对象。

    Note:
        default 按主题取 500/400 色阶，其余颜色固定取 500；未知颜色名静默回退到 primary，未做校验。
    """
    if name == "default":
        # default 在亮模式偏亮、暗模式偏深，避免和背景同色看不见
        return QColor(HEROUI_COLORS["default"][500 if theme == "light" else 400])
    palette = HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])
    return QColor(palette[500])


__all__ = [
    "VALID_COLORS",
    "VALID_SIZES",
    "VALID_VARIANTS",
    "resolve_indicator_color",
]
