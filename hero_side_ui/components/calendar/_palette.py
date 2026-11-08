"""Calendar 取色：语义色 × 主题 × 状态的背景/文字色集中解析，供 _cell 调用。"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS

# HeroUI 语义色的「on-color」文字色（对齐 xxx-foreground）：
# 除 warning 用深色字外，其余选中态都用白字。
_FOREGROUND_ON_COLOR = {
    "warning": "#000000",
}


def _shade(color: str, level: int) -> QColor:
    """从语义色阶取指定深度的颜色。

    Args:
        color: 语义色名；未命中回退 primary。
        level: 色阶深度（50~900）。

    Returns:
        对应色阶的 QColor。
    """
    ramp = HEROUI_COLORS.get(color, HEROUI_COLORS["primary"])
    return QColor(ramp[level])


def selected_bg(color: str, theme: str) -> QColor:
    """选中格背景色。

    Args:
        color: 语义色名或 foreground。
        theme: 主题名。

    Returns:
        语义色用 500；foreground 用主题前景色（暗底浅 / 亮底深）。
    """
    if color == "foreground":
        return QColor("#ecedee") if theme == "dark" else QColor("#11181c")
    return _shade(color, 500)


def selected_text(color: str, theme: str) -> QColor:
    """选中格文字色。

    Args:
        color: 语义色名或 foreground。
        theme: 主题名。

    Returns:
        语义色用对比前景色（多数白、warning 黑）；
        foreground 选中时字用主题背景色（与底反相）。
    """
    if color == "foreground":
        return QColor("#000000") if theme == "dark" else QColor("#ffffff")
    return QColor(_FOREGROUND_ON_COLOR.get(color, "#ffffff"))


def hover_bg(color: str, theme: str) -> QColor:
    """未选中格 hover 背景色。

    Args:
        color: 语义色名或 foreground。
        theme: 主题名。

    Returns:
        foreground 用 default-200；primary / secondary 取 50；
        success / warning / danger 暗色取 50、亮色取 100。
    """
    if color == "foreground":
        return _shade("default", 200)
    if color in ("primary", "secondary"):
        return _shade(color, 50)
    # success / warning / danger
    return _shade(color, 50 if theme == "dark" else 100)


def hover_text(color: str, theme: str) -> QColor:
    """未选中格 hover 文字色。

    Args:
        color: 语义色名或 foreground。
        theme: 主题名。

    Returns:
        按色阶取 400~600 的可读文字色。
    """
    if color == "foreground":
        return _shade("default", 600)
    if color in ("primary", "secondary"):
        return _shade(color, 400)
    return _shade(color, 500 if theme == "dark" else 600)


def normal_text(theme: str) -> QColor:
    """普通日期文字色。

    Args:
        theme: 主题名。

    Returns:
        主题前景色（本月、未选中、未 hover 状态）。
    """
    return QColor("#ffffff") if theme == "dark" else QColor("#11181c")


def disabled_text(theme: str) -> QColor:
    """禁用 / 本月外文字色。

    Args:
        theme: 主题名。

    Returns:
        暗色用 28% 透明的白色（色板不随主题反转）；
        亮色取 default-300。
    """
    if theme == "dark":
        c = QColor("#ffffff")
        c.setAlphaF(0.28)
        return c
    return _shade("default", 300)


def today_ring(color: str, theme: str) -> QColor:
    """今天标记色（未选中时下方圆点）。

    Args:
        color: 语义色名或 foreground。
        theme: 主题名。

    Returns:
        语义色用 500；foreground 用主题前景色。
    """
    if color == "foreground":
        return QColor("#ecedee") if theme == "dark" else QColor("#11181c")
    return _shade(color, 500)


# ---- 表面分层色（对齐 calendar.ts）----------------------------------
# headerWrapper + gridHeader(星期名行) = bg-content1（亮层）；
# base(日期区底) = bg-default-50（暗一档）。两区靠色差分隔（不画阴影带，
# 浅色主题下阴影带会显成突兀灰杠）。


def surface_content1(theme: str) -> QColor:
    """月/年标题栏背景（content1 层）。

    Args:
        theme: 主题名。

    Returns:
        暗色 #101114、亮色 #ffffff。
    """
    if theme == "dark":
        return QColor("#101114")
    return QColor("#ffffff")


def surface_base(theme: str) -> str:
    """日期区底色（与窗口背景同色）。

    Args:
        theme: 主题名。

    Returns:
        hex 色串供 QSS 使用；让日期主区融入外部背景，
        仅顶部 header / 星期名条（content1）浮起。
    """
    return "#0b0d12" if theme == "dark" else "#fafbfd"


def picker_highlight_bg(theme: str) -> QColor:
    """月/年选择器中央高亮条底色。

    Args:
        theme: 主题名。

    Returns:
        暗色手动取 #27272a（色板不随主题反转，default-100 恒浅白）；
        亮色取 default-200。
    """
    return QColor("#27272a") if theme == "dark" else _shade("default", 200)


# ---- 范围选择（RangeCalendar，对齐 calendar.ts isRange compoundVariants）----
# 中间格：浅底连接背景 + 语义色文字；端点：语义色实底 + 前景色文字。


def range_middle_bg(color: str, theme: str) -> QColor:
    """范围中间格的连接背景（before 伪元素）。

    Args:
        color: 语义色名或 foreground。
        theme: 主题名。

    Returns:
        foreground 用 10% 透明的反相色；
        primary / secondary / danger 取 50；success / warning 按主题取 50/100。
    """
    if color == "foreground":
        c = QColor("#000000") if theme == "light" else QColor("#ffffff")
        c.setAlphaF(0.10)
        return c
    if color in ("primary", "secondary", "danger"):
        return _shade(color, 50)
    # success / warning
    return _shade(color, 50 if theme == "dark" else 100)


def range_middle_text(color: str, theme: str) -> QColor:
    """范围中间格文字色。

    Args:
        color: 语义色名或 foreground。
        theme: 主题名。

    Returns:
        foreground 用主题前景色；语义色按主题取 500/600。
    """
    if color == "foreground":
        return QColor("#ecedee") if theme == "dark" else QColor("#11181c")
    if color in ("primary", "secondary"):
        return _shade(color, 500)
    return _shade(color, 500 if theme == "dark" else 600)
