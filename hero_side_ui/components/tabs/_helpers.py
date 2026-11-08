"""Tabs 包内私有 helper 函数（颜色解析、圆角映射等）。"""

from PySide6.QtGui import QColor

from ...themes import HEROUI_COLORS

# ============================================================
# 工具：选中态文字色 / 未选中文字色 / cursor 填充色 解析
# ============================================================


def _opt(d: dict, *keys, default=None):
    """按 keys 顺序返回字典中首个命中键的值。

    Args:
        d: 待查询的字典。
        *keys: 依次尝试的键名。
        default: 所有键都未命中时的返回值。

    Returns:
        首个命中键对应的值，或 default。
    """
    for k in keys:
        if k in d:
            return d[k]
    return default


def _resolve_unselected_text(theme: str) -> QColor:
    """返回未选中 tab 的文字色（text-default-500）。"""
    return QColor(HEROUI_COLORS["default"][500])


def _resolve_selected_text(variant: str, color: str, theme: str) -> QColor:
    """取选中态文字色：contrast 色（warning 黑/其余白），underlined 用主色 500。"""
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


def _resolve_cursor_fill(variant: str, color: str, theme: str) -> QColor | None:
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


def _resolve_list_bg(variant: str, theme: str) -> QColor | None:
    """tabList 背景色。"""
    if variant in ("light", "underlined", "bordered"):
        return None  # 透明
    # solid: bg-default-100 / dark:bg-default-50
    if theme == "light":
        return QColor(HEROUI_COLORS["default"][100])
    # 暗色 solid 背景：稍亮
    c = QColor(HEROUI_COLORS["default"][800])
    return c


def _resolve_list_border(variant: str, theme: str) -> QColor | None:
    """tabList 边框色（仅 bordered 变体）。"""
    if variant != "bordered":
        return None
    if theme == "light":
        return QColor(HEROUI_COLORS["default"][200])
    return QColor(HEROUI_COLORS["default"][700])


def _resolve_radius_px(radius: str, size: str, height: int) -> tuple:
    """取 (list_radius, tab_radius) 像素对；full 取高度一半。"""
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
