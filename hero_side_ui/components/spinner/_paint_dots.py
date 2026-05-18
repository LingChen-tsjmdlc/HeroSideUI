"""variant=wave / dots —— 3 个圆点。

HeroUI 原版 CSS:
    wave:  @keyframes sway { 0%/100%{translateY(0)} 50%{translateY(-150%)} }
           750ms ease infinite, dot[i].delay = 250ms*i
    dots:  @keyframes blink { 0%/100%{opacity:.2} 20%{opacity:1} }
           1.4s linear infinite, dot[i].delay = 200ms*i

驱动器:
    wave: 周期 750ms
    dots: 周期 1.4s
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter


N_DOTS = 3


def _sway_y(local_phase: float) -> float:
    """sway: 0%→0, 50%→-1.5, 100%→0；类 cos 形"""
    # sin(π*p)*1.5 在 0/1 处为 0、0.5 处为 1.5；正方向是上 → 取负
    return -math.sin(math.pi * local_phase) * 1.5


def _blink_alpha(local_phase: float) -> float:
    """blink: 0%→0.2, 20%→1, 100%→0.2  线性段。"""
    if local_phase <= 0.2:
        return 0.2 + (local_phase / 0.2) * 0.8
    return 1.0 - ((local_phase - 0.2) / 0.8) * 0.8


def paint_wave(
    painter: QPainter,
    w: int,
    h: int,
    indicator: QColor,
    dot_size: float,
    phase: float,
):
    """phase ∈ [0, 1)；驱动器周期 0.75s。HeroUI 在 wave/dots 上把 wrapper 平移
    一段以让 dot 向下扎根，这里我们居中，用动画偏移 -1.5*dot_size 营造起伏。"""
    cx = w / 2.0
    cy = h / 2.0
    delay = 250.0 / 750.0  # = 1/3

    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(indicator)

    spacing = dot_size * 1.5
    total_w = (N_DOTS - 1) * spacing
    start_x = cx - total_w / 2.0

    for i in range(N_DOTS):
        local = (phase + i * delay) % 1.0
        y_off = _sway_y(local) * dot_size  # 单位 = dot_size
        x = start_x + i * spacing
        y = cy + y_off + dot_size * 0.5  # +0.5*dot_size 让"基线"贴在中线下方
        painter.drawEllipse(QPointF(x, y), dot_size / 2.0, dot_size / 2.0)

    painter.restore()


def paint_dots(
    painter: QPainter,
    w: int,
    h: int,
    indicator: QColor,
    dot_size: float,
    phase: float,
):
    """phase ∈ [0, 1)；驱动器周期 1.4s。"""
    cx = w / 2.0
    cy = h / 2.0
    delay = 200.0 / 1400.0  # ≈ 0.143

    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)

    spacing = dot_size * 1.5
    total_w = (N_DOTS - 1) * spacing
    start_x = cx - total_w / 2.0

    for i in range(N_DOTS):
        local = (phase + i * delay) % 1.0
        alpha = _blink_alpha(local)
        c = QColor(indicator)
        c.setAlphaF(alpha)
        painter.setBrush(c)
        x = start_x + i * spacing
        painter.drawEllipse(QPointF(x, cy), dot_size / 2.0, dot_size / 2.0)

    painter.restore()


__all__ = ["paint_wave", "paint_dots", "N_DOTS"]
