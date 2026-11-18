"""Dialog 的九宫格定位：纯函数，不依赖窗口实例。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize


def split_placement(placement: str) -> tuple[str, str]:
    """把九宫格取值拆成 (列, 行)。

    Args:
        placement: 九宫格取值，如 top-left / center / bottom-right。

    Returns:
        列为 left / center / right，行为 top / middle / bottom。
    """
    parts = placement.split("-")
    col = "left" if "left" in parts else "right" if "right" in parts else "center"
    row = "top" if "top" in parts else "bottom" if "bottom" in parts else "middle"
    return col, row


def place(
    ref: QRect,
    size: QSize,
    placement: str,
    offset: tuple[int, int],
    avail: QRect,
) -> QPoint:
    """算出窗口左上角：先按九宫格贴参照区域，再加偏移，最后钳进可用区域。

    Args:
        ref: 参照区域（父窗口客户区或屏幕可用区域）。
        size: 窗口尺寸。
        placement: 九宫格取值。
        offset: 在九宫格位置上再偏移的 (dx, dy)。
        avail: 屏幕可用区域；窗口比它大时贴左上角。
    """
    col, row = split_placement(placement)
    if col == "left":
        x = ref.left()
    elif col == "right":
        x = ref.left() + ref.width() - size.width()
    else:
        x = ref.left() + (ref.width() - size.width()) // 2
    if row == "top":
        y = ref.top()
    elif row == "bottom":
        y = ref.top() + ref.height() - size.height()
    else:
        y = ref.top() + (ref.height() - size.height()) // 2
    return clamp_point(QPoint(x + offset[0], y + offset[1]), size, avail)


def clamp_point(pos: QPoint, size: QSize, avail: QRect) -> QPoint:
    """把窗口左上角钳到可用区域内；窗口比区域大时贴区域左上角。"""
    max_x = avail.left() + avail.width() - size.width()
    max_y = avail.top() + avail.height() - size.height()
    return QPoint(
        max(avail.left(), min(pos.x(), max_x)),
        max(avail.top(), min(pos.y(), max_y)),
    )


__all__ = ["clamp_point", "place", "split_placement"]
