"""Tooltip 定位纯函数：calc_position 返回 move 目标坐标（顶层为屏幕坐标，
embedded 为 ancestor 局部坐标）。
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QWidget

from ..._shared.overlays.bounds import overflow, popup_area
from ...core.shadow_paint import tier_margin
from ._constants import ARROW_SIZE

__all__ = [
    "calc_position",
    "compute_pos_for",
    "flip_placement",
    "frame_margins",
]


def frame_margins(
    shadow: str, show_arrow: bool, actual_placement: str
) -> tuple[int, int, int, int]:
    """内 layout 四方向让出空间给 arrow 和阴影。返回 (left, top, right, bottom)。"""
    sm = tier_margin(shadow)
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
    margins: tuple[int, int, int, int],
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
    my_size: tuple[int, int],
    margins: tuple[int, int, int, int],
    embedded: bool,
    anchor_ancestor: QWidget = None,
) -> tuple[QPoint, str]:
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
        pos = compute_pos_for(placement, origin, tr_w, tr_h, my_w, my_h, margins, offset_gap)

        # 越界检测以 ancestor rect 为边界
        anc = anchor_ancestor.rect()
        if (
            pos.x() < anc.left()
            or pos.y() < anc.top()
            or pos.x() + my_w > anc.right()
            or pos.y() + my_h > anc.bottom()
        ):
            flipped = flip_placement(placement)
            pos = compute_pos_for(flipped, origin, tr_w, tr_h, my_w, my_h, margins, offset_gap)
            return pos, flipped
        return pos, placement

    # 顶层模式
    tr_pos = trigger.mapToGlobal(QPoint(0, 0))
    tr_w = trigger.width()
    tr_h = trigger.height()

    # 可用区域 = 窗口客户区 ∩ trigger 所在屏（多屏下取主屏会把副屏 trigger 误判越界）。
    area = popup_area(trigger)
    pos = compute_pos_for(placement, tr_pos, tr_w, tr_h, my_w, my_h, margins, offset_gap)
    ml, mt, mr, mb = margins
    body = QRect(pos.x() + ml, pos.y() + mt, max(1, my_w - ml - mr), max(1, my_h - mt - mb))
    miss = overflow(body, area)
    if miss > 0:
        flipped = flip_placement(placement)
        new_pos = compute_pos_for(flipped, tr_pos, tr_w, tr_h, my_w, my_h, margins, offset_gap)
        new_body = QRect(
            new_pos.x() + ml, new_pos.y() + mt, max(1, my_w - ml - mr), max(1, my_h - mt - mb)
        )
        # 两边都放不下取越界更少的一边；仍越界的部分由 clip_to_host 裁掉
        if overflow(new_body, area) < miss:
            return new_pos, flipped

    return pos, placement
