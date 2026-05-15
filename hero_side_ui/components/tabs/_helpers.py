"""Tabs 包内私有 helper 函数（颜色解析、圆角映射等）。"""

from typing import Optional

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS



# ============================================================
# 工具：选中态文字色 / 未选中文字色 / cursor 填充色 解析
# ============================================================

def _opt(d: dict, *keys, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default


def _resolve_unselected_text(theme: str) -> QColor:
    """未选中 tab 文字色: HeroUI text-default-500"""
    return QColor(HEROUI_COLORS["default"][500])


def _resolve_selected_text(variant: str, color: str, theme: str) -> QColor:
    """选中态 tabContent 颜色:
    - solid/bordered/light: text-{color}-foreground 即对色的 contrast 文字色
        * default: light=#000 / dark=#fff
        * primary/secondary/success/danger: 对比白
        * warning: 对比黑
    - underlined: text-{color}（即色的主色 500）
        * default: light=#000 / dark=#fff（即 foreground）
    """
    if variant == "underlined":
        if color == "default":
            return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
        return QColor(HEROUI_COLORS[color][500])
    # solid/bordered/light: foreground 文字
    if color == "default":
        # default 选中态: foreground (light=黑, dark=白)
        return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
    if color == "warning":
        return QColor("#000000")
    return QColor("#FFFFFF")


def _resolve_cursor_fill(variant: str, color: str, theme: str) -> Optional[QColor]:
    """cursor 填充色（None 表示这个 variant 下不画填充 cursor）。"""
    if variant == "underlined":
        # underlined 下 cursor 是底边线条，不画矩形填充
        # 这里返回线条颜色
        if color == "default":
            return QColor("#000000") if theme == "light" else QColor("#FFFFFF")
        return QColor(HEROUI_COLORS[color][500])
    # solid / bordered / light: 矩形填充 cursor
    if color == "default":
        # bg-background 亮色 = 白；dark:bg-default 暗色 = default-100/200
        return QColor("#FFFFFF") if theme == "light" else QColor(HEROUI_COLORS["default"][700])
    return QColor(HEROUI_COLORS[color][500])


def _resolve_list_bg(variant: str, theme: str) -> Optional[QColor]:
    """tabList 背景色。"""
    if variant in ("light", "underlined", "bordered"):
        return None  # 透明
    # solid: bg-default-100 / dark:bg-default-50
    if theme == "light":
        return QColor(HEROUI_COLORS["default"][100])
    # 暗色 solid 背景：稍亮
    c = QColor(HEROUI_COLORS["default"][800])
    return c


def _resolve_list_border(variant: str, theme: str) -> Optional[QColor]:
    """tabList 边框色（仅 bordered 变体）。"""
    if variant != "bordered":
        return None
    if theme == "light":
        return QColor(HEROUI_COLORS["default"][200])
    return QColor(HEROUI_COLORS["default"][700])


def _resolve_radius_px(radius: str, size: str, height: int) -> tuple:
    """返回 (list_radius, tab_radius) 像素值。
    映射 HeroUI v2 tabs.ts:
        none -> (0, 0)
        sm   -> (medium=10, small=6)  我们项目 RADIUS sm=4 md=8 lg=14
        md   -> (medium, small)
        lg   -> (large, medium)
        full -> (height/2, height/2)
    我们映射:
        sm/md -> (8, 4)
        lg    -> (14, 8)
        none  -> (0, 0)
        full  -> (height/2, height/2)
    """
    if radius == "none":
        return (0, 0)
    if radius == "full":
        r = max(height // 2, 4)
        return (r, r)
    if radius == "sm":
        return (8, 4)
    if radius == "md":
        return (8, 4)
    if radius == "lg":
        return (14, 8)
    return (8, 4)

