"""Select 与 Autocomplete 共用的下拉列表高度计算。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

if TYPE_CHECKING:
    from ...components.listbox import Listbox
    from ...components.popover import Popover

# 触发控件与浮层之间的固定间距。
_POPOVER_GAP = 6
# 浮层滚动区的最小高度。
_MIN_HEIGHT = 80


def available_height_below(anchor: QWidget, popover: Popover, fallback: int) -> int:
    """计算触发控件下沿到屏幕可用区域底部可容纳的滚动区高度。

    Args:
        anchor: 触发控件。
        popover: 承载列表的浮层，用于扣除下边距。
        fallback: 没有可用屏幕时返回的高度。

    Returns:
        可用像素高度。
    """
    screen = QApplication.primaryScreen()
    if screen is None:
        return fallback
    bottom = screen.availableGeometry().bottom()
    top = anchor.mapToGlobal(QPoint(0, 0)).y() + anchor.height()
    return int(bottom - top - _POPOVER_GAP - popover.frame_margins()[3])


def fit_popup_height(
    scroll: QScrollArea,
    listbox: Listbox,
    token_max: int,
    available: int | None = None,
) -> None:
    """按内容和可用空间设置滚动区高度。

    内容不超过 token_max 的一半时随内容收缩；更长的列表固定为上限并滚动。

    Args:
        scroll: 包裹列表的滚动区。
        listbox: 列表，提供可见内容高度。
        token_max: 当前尺寸档位的高度上限。
        available: 触发控件下方可用高度；None 表示不受屏幕限制。
    """
    cap = token_max if available is None else min(token_max, available)
    cap = min(token_max, max(_MIN_HEIGHT, int(cap)))

    content = max(1, listbox.visible_content_height())
    if content > max(_MIN_HEIGHT, token_max // 2):
        target = cap
    else:
        target = max(_MIN_HEIGHT, min(content, cap))

    scroll.setMinimumHeight(target)
    scroll.setMaximumHeight(cap)
    scroll.updateGeometry()
