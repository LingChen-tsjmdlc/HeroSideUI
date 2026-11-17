"""Window 配色与几何计算：不依赖窗口实例的纯函数，便于单独测试。"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS, WINDOW_SPEC, WINDOW_TITLE_BAR_HEIGHTS
from ...themes.theme_values import get_background, get_foreground


def platform_system() -> str:
    """按当前操作系统解析 auto。

    Returns:
        windows / mac / linux。
    """
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def default_title_bar_height(system: str) -> int:
    """返回该风格的标准标题栏高度。

    Args:
        system: windows / mac / linux（已解析，不含 auto）。
    """
    return WINDOW_TITLE_BAR_HEIGHTS[system]


def clamp_title_bar_height(value: int) -> int:
    """把标题栏高度夹到下限以上。

    Args:
        value: 传入的高度，单位 px。
    """
    return max(WINDOW_SPEC["min_title_bar_height"], int(value))


# ============================================================
# 控制按钮尺寸
# ============================================================


def linux_diameter(title_bar_height: int) -> int:
    """linux 圆形按钮直径 = 栏高 - 16，最小 16。

    Args:
        title_bar_height: 标题栏高度。
    """
    return max(
        WINDOW_SPEC["linux_min_diameter"],
        title_bar_height - WINDOW_SPEC["linux_diameter_inset"],
    )


def mac_diameter(title_bar_height: int) -> int:
    """mac 圆点直径 = 栏高 x 16 / 28 取整，最小 16。

    Args:
        title_bar_height: 标题栏高度。
    """
    base_d, base_h = WINDOW_SPEC["mac_base_diameter"], WINDOW_SPEC["mac_base_height"]
    return max(base_d, round(title_bar_height * base_d / base_h))


def button_size(system: str, title_bar_height: int) -> tuple[int, int]:
    """单个控制按钮的宽高。

    Args:
        system: windows / mac / linux。
        title_bar_height: 标题栏高度。

    Returns:
        (宽, 高)。windows 宽度固定、高度随栏高；linux / mac 为圆，直径随栏高。
    """
    if system == "windows":
        return WINDOW_SPEC["windows_button_width"], title_bar_height
    d = linux_diameter(title_bar_height) if system == "linux" else mac_diameter(title_bar_height)
    return d, d


def controls_width(system: str, title_bar_height: int, count: int) -> int:
    """控制按钮组的总宽度。

    Args:
        system: windows / mac / linux。
        title_bar_height: 标题栏高度。
        count: 可见按钮个数；0 时组宽为 0。
    """
    if count <= 0:
        return 0
    w, _ = button_size(system, title_bar_height)
    if system == "windows":
        return w * count
    if system == "linux":
        pad, gap = WINDOW_SPEC["linux_side_padding"], WINDOW_SPEC["linux_button_gap"]
    else:
        pad, gap = WINDOW_SPEC["mac_side_padding"], WINDOW_SPEC["mac_gap"]
    return pad * 2 + w * count + gap * (count - 1)


def min_size_floor(system: str, title_bar_height: int, count: int) -> tuple[int, int]:
    """最小尺寸的默认下限：固定下限与按钮保底两者取大。

    Args:
        system: windows / mac / linux。
        title_bar_height: 标题栏高度。
        count: 可见控制按钮个数。

    Returns:
        (最小宽, 最小高)。
    """
    w = max(
        WINDOW_SPEC["min_width_floor"],
        controls_width(system, title_bar_height, count) + WINDOW_SPEC["min_width_extra"],
    )
    h = max(
        WINDOW_SPEC["min_height_floor"],
        title_bar_height + WINDOW_SPEC["min_height_extra"],
    )
    return w, h


# ============================================================
# 配色
# ============================================================


@dataclass(frozen=True)
class WindowColors:
    """一套主题下 Window 用到的全部颜色。"""

    background: QColor
    title_bar: QColor
    border: QColor
    foreground: QColor
    hover: QColor
    press: QColor
    mac_inactive: QColor


def _with_alpha(color: QColor, alpha: float) -> QColor:
    """返回带指定不透明度的副本。"""
    c = QColor(color)
    c.setAlphaF(alpha)
    return c


def window_colors(theme: str) -> WindowColors:
    """按主题取配色。

    Args:
        theme: light / dark。

    Note:
        HEROUI_COLORS 恒为亮色原始值，暗色下浅阶要索引镜像：100 -> 800、200 -> 700。
    """
    dark = theme == "dark"
    dc = HEROUI_COLORS["default"]
    fg = QColor(get_foreground(theme))
    return WindowColors(
        background=QColor(get_background(theme)),
        title_bar=QColor(dc[800] if dark else dc[100]),
        border=QColor(dc[700] if dark else dc[200]),
        foreground=fg,
        hover=_with_alpha(fg, 0.10),
        press=_with_alpha(fg, 0.16),
        mac_inactive=QColor(WINDOW_SPEC["mac_inactive_dark" if dark else "mac_inactive_light"]),
    )


__all__ = [
    "WindowColors",
    "button_size",
    "clamp_title_bar_height",
    "controls_width",
    "default_title_bar_height",
    "linux_diameter",
    "mac_diameter",
    "min_size_floor",
    "platform_system",
    "window_colors",
]
