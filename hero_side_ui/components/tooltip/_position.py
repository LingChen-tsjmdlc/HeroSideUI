"""Tooltip 几何 / 定位工具（纯函数）。

为什么独立出来：
    tooltip.py 已经接近铁律 8 的 800 行红线。把"placement → 坐标"这套
    纯几何逻辑（无 widget 状态依赖，只吃几何参数）迁出去后，主类瘦身
    专注事件 / 动画 / 装配。

核心入口：
    calc_position(...)  根据 embedded 模式与否，返回 tooltip 应当 move() 到的坐标。
                        - 顶层模式：屏幕坐标
                        - embedded 模式：anchor_ancestor 的局部坐标
"""

from __future__ import annotations

from typing import Tuple

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from ._constants import ARROW_SIZE

from ...themes import POPOVER_SHADOWS

__all__ = [
    "frame_margins",
    "flip_placement",
    "compute_pos_for",
    "calc_position",
]


def frame_margins(
    shadow: str, show_arrow: bool, actual_placement: str
) -> Tuple[int, int, int, int]:
    """内 layout 四方向让出空间给 arrow 和阴影。返回 (left, top, right, bottom)。"""
    cfg = POPOVER_SHADOWS.get(shadow, POPOVER_SHADOWS["sm"])
    sm = cfg["blur"] + abs(cfg["offset_y"])
    arrow = ARROW_SIZE if show_arrow else 0
    m = [sm, sm, sm, sm]
    if actual_placement.startswith("top"):
        m[3] += arrow
    elif actual_placement.startswith("bottom"):
        m[1] += arrow
    elif actual_placement.startswith("left"):
        m[2] += arrow
    elif actual_placement.startswith("right"):
        m[0] += arrow
    return tuple(m)  # type: ignore[return-value]


def flip_placement(p: str) -> str:
    """primary direction 翻转（top↔bottom，left↔right），保留 -start/-end 后缀。"""
    if p.startswith("top"):
        return p.replace("top", "bottom")
    if p.startswith("bottom"):
        return p.replace("bottom", "top")
    if p.startswith("left"):
        return p.replace("left", "right")
    if p.startswith("right"):
        return p.replace("right", "left")
    return p


def compute_pos_for(
    place: str,
    tr_pos: QPoint,
    tr_w: int,
    tr_h: int,
    my_w: int,
    my_h: int,
    margins: Tuple[int, int, int, int],
    gap: int,
) -> QPoint:
    """根据 placement 在给定原点上计算 tooltip 左上角。

    Args:
        place: 12 种 placement 之一（top / top-start / ... / right-end）
        tr_pos: trigger 在目标坐标系下的左上角（顶层用 global，embedded 用 ancestor-local）
        tr_w/tr_h: trigger 尺寸
        my_w/my_h: tooltip sizeHint
        margins: tooltip 内 layout 让出的 (l, t, r, b)（含阴影 + arrow 让位）
        gap: tooltip 与 trigger 边缘的额外距离（offset 参数）
    """
    ml, mt, mr, mb = margins
    x, y = tr_pos.x(), tr_pos.y()

    if place == "top":
        return QPoint(x + (tr_w - my_w) // 2, y - my_h + mb - gap)
    if place == "top-start":
        return QPoint(x - ml, y - my_h + mb - gap)
    if place == "top-end":
        return QPoint(x + tr_w - my_w + mr, y - my_h + mb - gap)

    if place == "bottom":
        return QPoint(x + (tr_w - my_w) // 2, y + tr_h - mt + gap)
    if place == "bottom-start":
        return QPoint(x - ml, y + tr_h - mt + gap)
    if place == "bottom-end":
        return QPoint(x + tr_w - my_w + mr, y + tr_h - mt + gap)

    if place == "left":
        return QPoint(x - my_w + mr - gap, y + (tr_h - my_h) // 2)
    if place == "left-start":
        return QPoint(x - my_w + mr - gap, y - mt)
    if place == "left-end":
        return QPoint(x - my_w + mr - gap, y + tr_h - my_h + mb)

    if place == "right":
        return QPoint(x + tr_w - ml + gap, y + (tr_h - my_h) // 2)
    if place == "right-start":
        return QPoint(x + tr_w - ml + gap, y - mt)
    if place == "right-end":
        return QPoint(x + tr_w - ml + gap, y + tr_h - my_h + mb)

    return QPoint(x, y + tr_h)


def calc_position(
    trigger: QWidget,
    placement: str,
    offset_gap: int,
    my_size: Tuple[int, int],
    margins: Tuple[int, int, int, int],
    embedded: bool,
    anchor_ancestor: QWidget = None,
) -> Tuple[QPoint, str]:
    """计算 tooltip 的目标坐标 + 实际 placement（含 auto-flip）。

    返回 (pos, actual_placement)：
        pos —— 顶层模式下是 global 坐标；embedded 下是 anchor_ancestor 的 local 坐标
        actual_placement —— 可能因 flip 而与传入的 placement 不同

    Args:
        trigger: 触发器 widget
        placement: 期望 placement
        offset_gap: tooltip 与 trigger 之间的额外像素距离
        my_size: tooltip 的 (width, height)（一般来自 sizeHint）
        margins: tooltip 内 layout 的 (l, t, r, b)（来自 frame_margins）
        embedded: 是否 embedded 模式
        anchor_ancestor: embedded 模式必填，作为坐标系基准
    """
    my_w, my_h = my_size

    if embedded and anchor_ancestor is not None:
        origin = trigger.mapTo(anchor_ancestor, QPoint(0, 0))
        tr_w = trigger.width()
        tr_h = trigger.height()
        pos = compute_pos_for(
            placement, origin, tr_w, tr_h, my_w, my_h, margins, offset_gap
        )

        # 越界检测以 ancestor rect 为边界
        anc = anchor_ancestor.rect()
        if (
            pos.x() < anc.left()
            or pos.y() < anc.top()
            or pos.x() + my_w > anc.right()
            or pos.y() + my_h > anc.bottom()
        ):
            flipped = flip_placement(placement)
            pos = compute_pos_for(
                flipped, origin, tr_w, tr_h, my_w, my_h, margins, offset_gap
            )
            return pos, flipped
        return pos, placement

    # 顶层模式
    tr_pos = trigger.mapToGlobal(QPoint(0, 0))
    tr_w = trigger.width()
    tr_h = trigger.height()

    # 用 trigger 实际所在的 screen，而不是 primaryScreen——
    # 多屏配置下 primaryScreen 的几何范围可能与 trigger 所在屏完全不同
    # （例如主屏在 (0,0,1920,1080)，副屏在 (1920,0,1920,1080)，trigger 在副屏），
    # 这时 tr_pos.x ~ 2500 永远 > primaryScreen.right=1920 → 所有 placement 都被误判
    # 越界 → top 全 flip 到 bottom、bottom 全 flip 到 top（与"位置反了"截图完全吻合）。
    win = trigger.window() if hasattr(trigger, "window") else None
    win_handle = win.windowHandle() if win is not None else None
    scr = win_handle.screen() if win_handle is not None else None
    if scr is None:
        scr = QGuiApplication.screenAt(tr_pos) or QGuiApplication.primaryScreen()
    screen = scr.availableGeometry()
    pos = compute_pos_for(
        placement, tr_pos, tr_w, tr_h, my_w, my_h, margins, offset_gap
    )

    rect = QRect(pos.x(), pos.y(), my_w, my_h)
    if (
        rect.left() < screen.left()
        or rect.top() < screen.top()
        or rect.right() > screen.right()
        or rect.bottom() > screen.bottom()
    ):
        flipped = flip_placement(placement)
        new_pos = compute_pos_for(
            flipped, tr_pos, tr_w, tr_h, my_w, my_h, margins, offset_gap
        )
        return new_pos, flipped

    return pos, placement
