"""Slider 几何纯函数：基于 canvas 坐标系，参数显式传入不依赖 self。"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QFontMetrics

from ...core import make_text_qfont
from ...themes import RADIUS

# 与 _paint.py / slider.py 共享的常量
RING_WIDTH = 2  # showOutline 时 thumb 外圈宽度
RING_GAP = 2  # ring 与 thumb 之间的留白
HALO_EXTRA = 6  # canvas 上下额外留白，避免 thumb 贴边裁剪

__all__ = [
    "HALO_EXTRA",
    "RING_GAP",
    "RING_WIDTH",
    "clamp_value",
    "hit_thumb",
    "marks_band_size",
    "ratio_at_pos",
    "ratio_of",
    "resolve_thumb_radius",
    "snap_value",
    "thumb_centers",
    "track_geom",
    "track_visual_geom",
    "value_at_ratio",
]


def marks_band_size(cfg: dict) -> int:
    """计算 marks 文字带高度（行高加 mark_offset 间距）。"""
    fm = QFontMetrics(make_text_qfont(cfg["mark_font_size"], "normal"))
    return fm.height() + cfg["mark_offset"]


def track_geom(
    cfg: dict,
    orientation: str,
    canvas_w: float,
    canvas_h: float,
    has_marks: bool,
) -> QRectF:
    """取 thumb 圆心轨迹矩形（供 thumb_centers/ratio_at_pos 计算）。"""
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
    """取 track 绘制矩形：沿主轴两端外延 (thumb-thickness)/2。

    Note:
        外延使 track 圆角端落在 thumb 外缘，消除 radius=full 时的尖缝隙；
        等价 HeroUI 的 border-x-transparent 方案。
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
    """把值线性映射为 0..1 比例，越界时截断。"""
    if vmax <= vmin:
        return 0.0
    return max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))


def value_at_ratio(r: float, vmin: float, vmax: float) -> float:
    """把 0..1 比例线性映射回值，r 越界时截断。"""
    r = max(0.0, min(1.0, r))
    return vmin + r * (vmax - vmin)


def thumb_centers(
    track: QRectF,
    orientation: str,
    vmin: float,
    vmax: float,
    value,  # float 或 (lo, hi)
    is_range: bool,
) -> list[QPointF]:
    """根据当前值计算 thumb 中心坐标列表。

    Note:
        垂直方向遵循 "下=min / 上=max"，对齐 HeroUI 的 flex-col-reverse 视觉。
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
    centers: list[QPointF],
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
    """把圆角档位解析为 thumb 的像素圆角。

    Note:
        对齐 HeroUI tailwind-variants：none 为 0，sm / md 取对应半径的一半，
        lg 取 large/1.5，full 为 thumb 半径（正圆）。
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
    """把值截断到 [vmin, vmax] 区间。"""
    return max(vmin, min(vmax, v))


def snap_value(v: float, vmin: float, vmax: float, step: float) -> float:
    """按 step snap 并 clamp。"""
    if step <= 0:
        return clamp_value(v, vmin, vmax)
    n = round((v - vmin) / step)
    snapped = vmin + n * step
    return clamp_value(round(snapped, 10), vmin, vmax)
