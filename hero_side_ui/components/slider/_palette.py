"""Slider 颜色纯函数：filler/thumb 语义色 500，track default-300/50 等规则。"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS

__all__ = [
    "filler_color",
    "inner_dot_color",
    "resolve_color",
    "ring_color",
    "step_dot_in_range",
    "step_dot_out_of_range",
    "thumb_color",
    "track_bg_color",
]


def resolve_color(name: str, theme: str) -> QColor:
    """把语义色名解析为 QColor。

    Note:
        foreground / default 跟随主题翻转黑白；其他色返回 palette[500]。
    """
    if name in ("foreground", "default"):
        return QColor("#ecedee" if theme == "dark" else "#11181c")
    palette = HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])
    return QColor(palette[500])


def track_bg_color(theme: str) -> QColor:
    """返回 track 背景色，亮底取 default-300/50、暗底取 600/50。"""
    is_dark = theme == "dark"
    c = QColor(HEROUI_COLORS["default"][600 if is_dark else 300])
    c.setAlphaF(0.5)
    return c


def filler_color(name: str, theme: str) -> QColor:
    """返回 filler 颜色，等价于按语义色解析。"""
    return resolve_color(name, theme)


def thumb_color(name: str, theme: str) -> QColor:
    """返回 thumb 颜色，等价于按语义色解析。"""
    return resolve_color(name, theme)


def inner_dot_color(theme: str) -> QColor:
    """返回 inner dot 背景色，亮底白、暗底黑。"""
    return QColor("#000000" if theme == "dark" else "#ffffff")


def ring_color(theme: str) -> QColor:
    """返回 ring 颜色，与 inner dot 一致。"""
    return inner_dot_color(theme)


def step_dot_in_range(theme: str) -> QColor:
    """返回范围内 step 点的半透明背景色。"""
    c = inner_dot_color(theme)
    c.setAlphaF(0.5)
    return c


def step_dot_out_of_range(size: str) -> QColor:
    """返回范围外 step 点颜色，size=sm 用 default-200、其余用 default-300。"""
    if size in ("sm", "small"):
        c = QColor(HEROUI_COLORS["default"][200])
    else:
        c = QColor(HEROUI_COLORS["default"][300])
    c.setAlphaF(0.7)
    return c
