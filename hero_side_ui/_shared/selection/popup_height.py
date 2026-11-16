"""Select 与 Autocomplete 共用的下拉列表高度计算。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QScrollArea, QWidget

from ..overlays.bounds import space_above, space_below

if TYPE_CHECKING:
    from ...components.listbox import Listbox
    from ...components.popover import Popover

# 触发控件与浮层之间的固定间距。
_POPOVER_GAP = 6
# 浮层滚动区的最小高度。
_MIN_HEIGHT = 80


def available_height_below(anchor: QWidget, popover: Popover, fallback: int) -> int:
    """触发控件在宿主窗口内可容纳的滚动区高度。

    Args:
        anchor: 触发控件。
        popover: 承载列表的浮层（保留参数以兼容旧调用）。
        fallback: 拿不到窗口信息时返回的高度。

    Note:
        优先向下：下方够放最小列表就按下方空间算（内容多时由列表滚动承接）；
        下方比最小列表还小，Popover 会翻到上方，这时按上下较大的一侧算。
        函数名沿用旧名。
    """
    try:
        below = int(space_below(anchor) - _POPOVER_GAP)
        if below >= _MIN_HEIGHT:
            return below
        return max(below, int(space_above(anchor) - _POPOVER_GAP))
    except RuntimeError:
        return fallback


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
        available: 触发控件下方可用高度；None 表示不受窗口限制。
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
