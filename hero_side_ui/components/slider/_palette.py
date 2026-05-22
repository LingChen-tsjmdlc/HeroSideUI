"""Slider 颜色解析（纯函数，按 color/theme/size 显式传入，不依赖 self）。

所有颜色规则对齐 HeroUI v2 slider.ts:
    - filler/thumb: 语义色 500 级；foreground/default → light:#11181c / dark:#ecedee
    - track 背景: bg-default-300/50 (light) / 600/50 (dark)
    - inner-dot / ring: bg-background (light:#fff / dark:#000)
    - step-dot in-range: bg-background/50；out-of-range: default-200 (sm) / 300 (其他)
"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS

__all__ = [
    "resolve_color",
    "track_bg_color",
    "filler_color",
    "thumb_color",
    "inner_dot_color",
    "ring_color",
    "step_dot_in_range",
    "step_dot_out_of_range",
]


def resolve_color(name: str, theme: str) -> QColor:
    """语义色 → QColor。

    foreground/default 跟随主题翻转黑白；其他色返回 palette[500]。
    """
    if name in ("foreground", "default"):
        return QColor("#ecedee" if theme == "dark" else "#11181c")
    palette = HEROUI_COLORS.get(name, HEROUI_COLORS["primary"])
    return QColor(palette[500])


def track_bg_color(theme: str) -> QColor:
    """track 背景: bg-default-300/50 (light) / 600/50 (dark)"""
    is_dark = theme == "dark"
    c = QColor(HEROUI_COLORS["default"][600 if is_dark else 300])
    c.setAlphaF(0.5)
    return c


def filler_color(name: str, theme: str) -> QColor:
    return resolve_color(name, theme)


def thumb_color(name: str, theme: str) -> QColor:
    return resolve_color(name, theme)


def inner_dot_color(theme: str) -> QColor:
    """bg-background: light=#fff / dark=#000"""
    return QColor("#000000" if theme == "dark" else "#ffffff")


def ring_color(theme: str) -> QColor:
    """ring 同 inner_dot（HeroUI: ring-background）"""
    return inner_dot_color(theme)


def step_dot_in_range(theme: str) -> QColor:
    """data-[in-range=true]:bg-background/50"""
    c = inner_dot_color(theme)
    c.setAlphaF(0.5)
    return c


def step_dot_out_of_range(size: str) -> QColor:
    """size=sm 用 default-200，否则 default-300（与主题无关，保持低饱和灰）"""
    if size in ("sm", "small"):
        c = QColor(HEROUI_COLORS["default"][200])
    else:
        c = QColor(HEROUI_COLORS["default"][300])
    c.setAlphaF(0.7)
    return c
