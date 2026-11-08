"""default 变体：实色 90° 弧（头）+ 3 个拖尾小圆点（虚，角度随速度伸缩）。"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

_TAIL_ALPHAS = (0.75, 0.50, 0.28)


def paint_default(
    painter: QPainter,
    w: int,
    h: int,
    indicator: QColor,
    border: float,
    phase_ease: float,
    phase_linear: float,  # 保留参数兼容，default 不再使用第二条驱动器
):
    """绘制 default 变体：实色 90° 弧头与随相位伸缩的 3 个拖尾圆点。

    Args:
        painter: 目标 QPainter，函数内会改写其画笔与画刷。
        w: 绘制区域宽度。
        h: 绘制区域高度。
        indicator: 主色，拖尾点由它派生并逐级降低透明度。
        border: 弧线宽度，同时决定拖尾点半径。
        phase_ease: 缓动相位，取值 [0, 1)，驱动器周期 0.8s。
        phase_linear: 线性相位，为兼容保留，本变体不使用。

    Note:
        default 不再使用第二条驱动器，函数体显式 del phase_linear 声明未使用。
    """
    del phase_linear  # 显式声明未使用

    side = min(w, h)
    margin = border / 2.0 + 1.0
    rect = QRectF(
        (w - side) / 2 + margin,
        (h - side) / 2 + margin,
        side - margin * 2,
        side - margin * 2,
    )
    cx = rect.center().x()
    cy = rect.center().y()
    radius = rect.width() / 2.0

    # ---- 3 阶 smoothstep：温和顿挫 ----
    t = phase_ease
    eased = t * t * (3.0 - 2.0 * t)
    rotation = eased * 360.0  # 顺时针前进度数

    # 头部角度（math 坐标系：0=右、逆时针正；与 Qt drawArc 起始角同向）
    # 12 点钟 = 90°；顺时针前进 = 角度递减
    head = 90.0 - rotation

    # ---- 实色 90° 弧（头） ----
    pen1 = QPen(indicator, border)
    pen1.setStyle(Qt.PenStyle.SolidLine)
    pen1.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen1)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    start_deg = head - 45.0
    span_deg = 90.0
    painter.drawArc(rect, int(start_deg * 16), int(span_deg * 16))

    # ---- 4 个拖尾点（虚） ----
    # 瞬时速度（cubic 导数）：6 t (1-t)，峰值 1.5 在 t=0.5
    # 慢的时候紧（gap 小），快的时候松（gap 大）
    # 使用 smoothstep 让松紧变化更平滑
    speed = 6.0 * t * (1.0 - t)  # [0, 1.5]
    speed_norm = speed / 1.5  # 归一化到 [0, 1]，慢=0, 快=1
    # smoothstep: 3x² - 2x³，让变化更平滑
    smooth = speed_norm * speed_norm * (3.0 - 2.0 * speed_norm)
    base_gap = 26.0  # 度（原 13.0，user 要求至少 2 倍间距）
    # smooth=0(慢) → gap=base_gap*0.5(更紧), smooth=1(快) → gap=base_gap*1.3(松)
    gap = base_gap * (0.5 + smooth * 0.8)

    # 弧的尾端（"后方" = Qt/math 角度增大方向）
    tail_start = head + 45.0
    dot_radius = max(1.0, border * 0.55)

    painter.setPen(Qt.PenStyle.NoPen)
    for i in range(3):
        ang = tail_start + gap * (i + 1)
        c = QColor(indicator)
        c.setAlphaF(_TAIL_ALPHAS[i])
        painter.setBrush(c)
        rad = math.radians(ang)
        # math → Qt 屏幕坐标（y 翻转）
        px = cx + radius * math.cos(rad)
        py = cy - radius * math.sin(rad)
        painter.drawEllipse(QPointF(px, py), dot_radius, dot_radius)


__all__ = ["paint_default"]
