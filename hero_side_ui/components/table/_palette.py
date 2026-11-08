"""Table 颜色纯函数：th/选中行条/hover/斑马/禁用 token，对齐 table.ts。"""

from __future__ import annotations

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS, RADIUS

__all__ = [
    "cell_text",
    "cell_text_disabled",
    "divider",
    "header_bg",
    "header_text",
    "header_text_hover",
    "hover_before_bg",
    "resolve_radius_px",
    "selected_before_bg",
    "selected_text",
    "striped_before_bg",
    "wrapper_bg",
]

_TRANSPARENT = QColor(0, 0, 0, 0)


def wrapper_bg(theme: str) -> QColor:
    """返回表体实心底色。

    Args:
        theme: 主题名；light 取白色，dark 取 default-900。

    Returns:
        恒为不透明的 QColor 底色。

    Note:
        滚动区内必须铺不透明底，否则半透明行条叠在未清空缓冲上会黑底加重影。
    """
    dc = HEROUI_COLORS["default"]
    return QColor("#ffffff") if theme == "light" else QColor(dc[900])


def _pal(color: str) -> dict:
    """按语义色名取调色板，未知色回退 default。

    Args:
        color: 语义色名。

    Returns:
        对应的调色板字典。

    Note:
        color 不在 HEROUI_COLORS 时回退到 default，未做校验。
    """
    return HEROUI_COLORS.get(color, HEROUI_COLORS["default"])


def header_bg(theme: str) -> QColor:
    """表头底色（th bg-default-100）。light 浅灰，dark 深灰（语义同为 default-100 角色）。"""
    dc = HEROUI_COLORS["default"]
    # light: default-100 浅灰；dark: default-100 在暗色语义里是深灰块 → 取 800
    return QColor(dc[100]) if theme == "light" else QColor(dc[800])


def header_text(theme: str) -> QColor:
    """表头字色（text-foreground-500）。"""
    dc = HEROUI_COLORS["default"]
    return QColor(dc[500]) if theme == "light" else QColor(dc[400])


def header_text_hover(theme: str) -> QColor:
    """表头 hover 字色（text-foreground-400），可排序列 hover 时略提亮。"""
    dc = HEROUI_COLORS["default"]
    return QColor(dc[600]) if theme == "light" else QColor(dc[300])


def cell_text(theme: str) -> QColor:
    """数据单元格默认字色（foreground）。"""
    dc = HEROUI_COLORS["default"]
    return QColor(dc[800]) if theme == "light" else QColor(dc[100])


def cell_text_disabled(theme: str) -> QColor:
    """禁用行字色（group-data-[disabled]/tr:text-foreground-300）。"""
    dc = HEROUI_COLORS["default"]
    return QColor(dc[300]) if theme == "light" else QColor(dc[600])


def selected_before_bg(color: str, theme: str) -> QColor:
    """返回选中行条的背景色。

    Args:
        color: 语义色名。
        theme: 主题名。

    Returns:
        带透明度的 QColor。

    Note:
        default 取 default 色阶并设 0.45 透明度，其余语义色取 500 并设 0.20。
    """
    if color == "default":
        c = QColor(HEROUI_COLORS["default"][400 if theme == "light" else 600])
        c.setAlphaF(0.45)
        return c
    c = QColor(_pal(color)[500])
    c.setAlphaF(0.20)
    return c


def selected_text(color: str, theme: str) -> QColor:
    """选中行字色（td data-selected text-*）。"""
    if color == "default":
        # default-foreground：light 深字 / dark 浅字
        return QColor("#000000") if theme == "light" else QColor("#ffffff")
    pal = _pal(color)
    if color in ("success", "warning"):
        return QColor(pal[600]) if theme == "light" else QColor(pal[400])
    if color == "danger":
        return QColor(pal[500]) if theme == "light" else QColor(pal[400])
    # primary / secondary: text-primary（500）
    return QColor(pal[500]) if theme == "light" else QColor(pal[400])


def hover_before_bg(theme: str) -> QColor:
    """未选中行 hover 行条背景（isSelectable hover before:bg-default-100 opacity-70）。"""
    dc = HEROUI_COLORS["default"]
    c = QColor(dc[100]) if theme == "light" else QColor(dc[800])
    c.setAlphaF(0.70)
    return c


def striped_before_bg(theme: str) -> QColor:
    """斑马纹奇数行行条背景（isStriped before:bg-default-100）。"""
    dc = HEROUI_COLORS["default"]
    return QColor(dc[100]) if theme == "light" else QColor(dc[800])


def divider(theme: str) -> QColor:
    """表头与内容之间的分隔线色。"""
    dc = HEROUI_COLORS["default"]
    return QColor(dc[200]) if theme == "light" else QColor(dc[700])


def resolve_radius_px(radius: str, height: int) -> int:
    """对齐 HeroUI rounded-* token 到像素；full = 高度的一半（药丸）。"""
    if radius == "none":
        return 0
    if radius == "full":
        return max(int(height) // 2, 4)
    raw = RADIUS.get(radius, RADIUS["lg"])
    return int(float(str(raw).rstrip("px")))
