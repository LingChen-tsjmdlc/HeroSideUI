"""
颜色相关工具函数
"""

from PySide6.QtGui import QColor


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """将 HEX 颜色转为 rgba() 格式

    Args:
        hex_color: HEX 颜色值，如 "#006FEE"
        alpha: 透明度 0.0 ~ 1.0

    Returns:
        rgba() 格式字符串，如 "rgba(0, 111, 238, 0.5)"
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def aligned_color_pair(start: QColor, end: QColor) -> tuple[QColor, QColor]:
    """让 alpha=0 端继承另一端 RGB，避免 lerp 经过黑色出现半透明灰瞬态。

    适用 transparent ↔ 实色的 hover/checked 过渡动画。
    """
    if start.alpha() == 0 and end.alpha() != 0:
        s = QColor(end)
        s.setAlpha(0)
        return s, QColor(end)
    if end.alpha() == 0 and start.alpha() != 0:
        e = QColor(start)
        e.setAlpha(0)
        return QColor(start), e
    return QColor(start), QColor(end)
