"""Slider 几何计算（纯函数）。

所有计算都基于 canvas 坐标系。参数显式传入（cfg 字典 + orientation + 标志位 +
当前值），不依赖 self —— 方便单测、方便 _paint.py 复用。

约定：
    - cfg: SLIDER_SIZES[size] 字典（含 thumb / track_thickness / mark_offset / mark_font_size）
    - orientation: "horizontal" / "vertical"
    - canvas_size: (width, height)
"""

from __future__ import annotations

import math
from typing import List, Tuple

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QFontMetrics

from ...core import make_text_qfont
from ...themes import RADIUS

# 与 _paint.py / slider.py 共享的常量
RING_WIDTH = 2  # showOutline 时 thumb 外圈宽度
RING_GAP = 2  # ring 与 thumb 之间的留白
HALO_EXTRA = 6  # canvas 上下额外留白，避免 thumb 贴边裁剪

__all__ = [
    "RING_WIDTH",
    "RING_GAP",
    "HALO_EXTRA",
    "marks_band_size",
    "track_geom",
    "track_visual_geom",
    "thumb_centers",
    "hit_thumb",
    "ratio_at_pos",
    "ratio_of",
    "value_at_ratio",
    "resolve_thumb_radius",
    "snap_value",
    "clamp_value",
]


def marks_band_size(cfg: dict) -> int:
    """marks 文字带的高度（行高 + mark_offset 间距）"""
    fm = QFontMetrics(make_text_qfont(cfg["mark_font_size"], "normal"))
    return fm.height() + cfg["mark_offset"]


def track_geom(
    cfg: dict,
    orientation: str,
    canvas_w: float,
    canvas_h: float,
    has_marks: bool,
) -> QRectF:
    """canvas 坐标系下 track 矩形。

    水平：左右各留 thumb 半径 + ring 余量；marks 占下方 mark_band。
    垂直：上下各留 thumb 半径 + ring 余量；marks 占右侧。
    """
    thumb = cfg["thumb"]
    thickness = cfg["track_thickness"]
    margin = thumb / 2 + RING_WIDTH + RING_GAP

    if orientation == "vertical":
        # marks 在右侧；track 居中在左侧 thumb 区
        track_x = (thumb / 2 + RING_WIDTH + RING_GAP) - thickness / 2
        track_y = margin
        track_h = canvas_h - margin * 2
        return QRectF(track_x, track_y, thickness, track_h)
    # 水平
    mark_band = marks_band_size(cfg) if has_marks else 0
    track_x = margin
    track_w = canvas_w - margin * 2
    track_y = (canvas_h - mark_band - thickness) / 2
    return QRectF(track_x, track_y, track_w, thickness)


def track_visual_geom(
    cfg: dict,
    orientation: str,
    canvas_w: float,
    canvas_h: float,
    has_marks: bool,
) -> QRectF:
    """track 的"绘制用"矩形（专供 _paint 用）。

    `track_geom` 返回的是"thumb 圆心轨迹"矩形（端点 = thumb 在 0%/100% 时的圆心），
    用于 `thumb_centers` / `ratio_at_pos` 等位置计算 —— 这些必须保持不变。

    但在 `radius=full` + 大尺寸时，如果 track 底色和 filler 也只画到 thumb 圆心，
    thumb 圆形伸出圆心那段（半径 thumb/2）会和 track 之间出现尖缝隙（圆角 thumb 的
    左/右半圆边缘 vs 矩形 track 的端部）。

    HeroUI 的解法是 `border-x-[thumb/2] border-x-transparent` —— 让 track 在两端
    各预留 thumb/2 宽的"透明 border"，filler 把 border 染色后就刚好钻到 thumb 下方。

    我们用等价的 PySide 几何修正：track 的可视矩形沿主轴方向**两端各向外延伸
    `(thumb - thickness) / 2`**，让 track 圆角端 (radius = thickness/2) 的最外
    像素正好落在 thumb 外缘。这样 thumb 任何半径模式下与 track 都是无缝衔接的。
    """
    inner = track_geom(cfg, orientation, canvas_w, canvas_h, has_marks)
    thumb = cfg["thumb"]
    thickness = cfg["track_thickness"]
    outset = max(0.0, (thumb - thickness) / 2.0)
    if outset <= 0:
        return inner
    if orientation == "vertical":
        return QRectF(
            inner.x(),
            inner.y() - outset,
            inner.width(),
            inner.height() + outset * 2,
        )
    return QRectF(
        inner.x() - outset,
        inner.y(),
        inner.width() + outset * 2,
        inner.height(),
    )


def ratio_of(v: float, vmin: float, vmax: float) -> float:
    if vmax <= vmin:
        return 0.0
    return max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))


def value_at_ratio(r: float, vmin: float, vmax: float) -> float:
    r = max(0.0, min(1.0, r))
    return vmin + r * (vmax - vmin)


def thumb_centers(
    track: QRectF,
    orientation: str,
    vmin: float,
    vmax: float,
    value,  # float 或 (lo, hi)
    is_range: bool,
) -> List[QPointF]:
    """根据当前值计算 thumb 中心坐标列表。

    垂直方向 "下=min / 上=max"（HeroUI flex-col-reverse 视觉）。
    """
    if orientation == "vertical":
        cx = track.center().x()

        def _y(v: float) -> float:
            r = ratio_of(v, vmin, vmax)
            return track.bottom() - r * track.height()

        if is_range:
            lo, hi = value
            return [QPointF(cx, _y(lo)), QPointF(cx, _y(hi))]
        return [QPointF(cx, _y(value))]

    cy = track.center().y()

    def _x(v: float) -> float:
        r = ratio_of(v, vmin, vmax)
        return track.left() + r * track.width()

    if is_range:
        lo, hi = value
        return [QPointF(_x(lo), cy), QPointF(_x(hi), cy)]
    return [QPointF(_x(value), cy)]


def hit_thumb(
    pt: QPointF,
    centers: List[QPointF],
    thumb_size: float,
    hide_thumb: bool,
) -> int:
    """命中测试：返回最近的 thumb 索引；都没命中返回 -1。"""
    if hide_thumb:
        return -1
    radius = thumb_size / 2 + RING_WIDTH + RING_GAP
    best = -1
    best_d = radius + 1
    for i, c in enumerate(centers):
        d = math.hypot(pt.x() - c.x(), pt.y() - c.y())
        if d <= radius and d < best_d:
            best = i
            best_d = d
    return best


def ratio_at_pos(pt: QPointF, track: QRectF, orientation: str) -> float:
    """点击位置 → 0..1 比例。垂直方向 "下=min / 上=max"。"""
    if orientation == "vertical":
        if track.height() <= 0:
            return 0.0
        r = (track.bottom() - pt.y()) / track.height()
    else:
        if track.width() <= 0:
            return 0.0
        r = (pt.x() - track.left()) / track.width()
    return max(0.0, min(1.0, r))


def resolve_thumb_radius(radius_token: str, thumb_size: float) -> float:
    """thumb 圆角（对齐 HeroUI tailwind-variants）：
    none → 0；sm → small/2；md → medium/2；lg → large/1.5；full → thumb/2 (圆)
    """
    r = radius_token
    if r in ("none", "no"):
        return 0.0
    if r in ("sm", "small"):
        return float(RADIUS["sm"].rstrip("px")) / 2  # 4/2
    if r in ("md", "medium"):
        return float(RADIUS["md"].rstrip("px")) / 2  # 8/2
    if r in ("lg", "large"):
        return float(RADIUS["lg"].rstrip("px")) / 1.5  # 14/1.5
    return thumb_size / 2.0  # full


def clamp_value(v: float, vmin: float, vmax: float) -> float:
    return max(vmin, min(vmax, v))


def snap_value(v: float, vmin: float, vmax: float, step: float) -> float:
    """按 step snap 并 clamp。"""
    if step <= 0:
        return clamp_value(v, vmin, vmax)
    n = round((v - vmin) / step)
    snapped = vmin + n * step
    return clamp_value(round(snapped, 10), vmin, vmax)
