"""Calendar 取色逻辑（对照 calendar.ts 的 color × 状态 compoundVariants）。

集中解析「某语义色在某主题下，各状态（选中/hover/选中+hover/today）应显示
什么背景色与文字色」，供 _cell 自绘调用，避免把大量 if-color 散进绘制代码。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS

# HeroUI 语义色的「on-color」文字色（对齐 xxx-foreground）：
# 除 warning 用深色字外，其余选中态都用白字。
_FOREGROUND_ON_COLOR = {
    "warning": "#000000",
}


def _shade(color: str, level: int) -> QColor:
    ramp = HEROUI_COLORS.get(color, HEROUI_COLORS["primary"])
    return QColor(ramp[level])


def selected_bg(color: str, theme: str) -> QColor:
    """选中格背景。语义色用 500；foreground 用主题前景色（暗底浅/亮底深）。"""
    if color == "foreground":
        return QColor("#ecedee") if theme == "dark" else QColor("#11181c")
    return _shade(color, 500)


def selected_text(color: str, theme: str) -> QColor:
    """选中格文字。语义色用对比前景色（多数白，warning 黑）；
    foreground 选中时字用主题背景色（与底反相）。"""
    if color == "foreground":
        return QColor("#000000") if theme == "dark" else QColor("#ffffff")
    return QColor(_FOREGROUND_ON_COLOR.get(color, "#ffffff"))


def hover_bg(color: str, theme: str) -> QColor:
    """未选中 hover 背景。

    对齐 calendar.ts：foreground 用 default-200；其余语义色浅色端
    （primary/secondary 用 50，success/warning/danger 亮色下 100、暗色下 50）。
    """
    if color == "foreground":
        return _shade("default", 200)
    if color in ("primary", "secondary"):
        return _shade(color, 50)
    # success / warning / danger
    return _shade(color, 50 if theme == "dark" else 100)


def hover_text(color: str, theme: str) -> QColor:
    """未选中 hover 文字色。"""
    if color == "foreground":
        return _shade("default", 600)
    if color in ("primary", "secondary"):
        return _shade(color, 400)
    return _shade(color, 500 if theme == "dark" else 600)


def normal_text(theme: str) -> QColor:
    """普通（本月、未选中、未 hover）日期文字色 = 主题前景色。"""
    return QColor("#ffffff") if theme == "dark" else QColor("#11181c")


def disabled_text(theme: str) -> QColor:
    """禁用 / 本月外日期文字色。

    HEROUI_COLORS 色板不随主题反转，default-300(#d4d4d8) 在暗底上反而偏亮。
    暗色改用低透明度的浅色（更淡、更隐退）；亮色用 default-300。
    """
    if theme == "dark":
        c = QColor("#ffffff")
        c.setAlphaF(0.28)
        return c
    return _shade("default", 300)


def today_ring(color: str, theme: str) -> QColor:
    """今天标记色（未选中时下方圆点）。语义色用 500；foreground 用主题前景色。"""
    if color == "foreground":
        return QColor("#ecedee") if theme == "dark" else QColor("#11181c")
    return _shade(color, 500)


# ---- 表面分层色（对齐 calendar.ts）----------------------------------
# headerWrapper + gridHeader(星期名行) = bg-content1（亮层）；
# base(日期区底) = bg-default-50（暗一档）。两区靠色差分隔（不画阴影带，
# 浅色主题下阴影带会显成突兀灰杠）。

def surface_content1(theme: str) -> QColor:
    """标题栏 / 星期名行背景（content1）。"""
    return QColor("#18181b") if theme == "dark" else QColor("#ffffff")


def surface_base(theme: str) -> str:
    """日期区底色：与窗口背景同色（对齐 ThemeProvider 的 window 背景），让日期
    主区融入外部背景，仅顶部 header/星期名条(content1)浮起。返回 hex 供 QSS 用。"""
    return "#0b0d12" if theme == "dark" else "#fafbfd"


def picker_highlight_bg(theme: str) -> QColor:
    """月/年选择器中央高亮条底色。HEROUI_COLORS 色板不随主题反转（default-100
    恒为浅白），故暗色手动取比 content1(#18181b) 亮一档的深灰 #27272a。"""
    return QColor("#27272a") if theme == "dark" else _shade("default", 200)


# ---- 范围选择（RangeCalendar，对齐 calendar.ts isRange compoundVariants）----
# 中间格：浅底连接背景 + 语义色文字；端点：语义色实底 + 前景色文字。

def range_middle_bg(color: str, theme: str) -> QColor:
    """范围中间格的连接背景（before 伪元素）。"""
    if color == "foreground":
        c = QColor("#000000") if theme == "light" else QColor("#ffffff")
        c.setAlphaF(0.10)
        return c
    if color in ("primary", "secondary", "danger"):
        return _shade(color, 50)
    # success / warning
    return _shade(color, 50 if theme == "dark" else 100)


def range_middle_text(color: str, theme: str) -> QColor:
    """范围中间格文字色。"""
    if color == "foreground":
        return QColor("#ecedee") if theme == "dark" else QColor("#11181c")
    if color in ("primary", "secondary"):
        return _shade(color, 500)
    return _shade(color, 500 if theme == "dark" else 600)
