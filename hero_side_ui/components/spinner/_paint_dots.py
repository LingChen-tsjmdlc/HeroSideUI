"""wave/dots 变体：3 圆点上下波动（750ms）或间歇闪烁（1.4s）。"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter

N_DOTS = 3


def _sway_y(local_phase: float) -> float:
    """按正弦曲线计算单个圆点的纵向起伏偏移。

    Args:
        local_phase: 单个圆点的局部相位，取值 [0, 1)。

    Returns:
        以 dot_size 为单位的纵向偏移，取负值表示向上。
    """
    # sin(π*p)*1.5 在 0/1 处为 0、0.5 处为 1.5；正方向是上 → 取负
    return -math.sin(math.pi * local_phase) * 1.5


def _blink_alpha(local_phase: float) -> float:
    """按分段线性曲线计算单个圆点的闪烁透明度。

    Args:
        local_phase: 单个圆点的局部相位，取值 [0, 1)。

    Returns:
        透明度 alpha，由 0.2 线性升至 20% 相位处的 1.0，再线性回落到 0.2。
    """
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
    """绘制 wave 变体：3 个圆点按相位错开做上下起伏。

    Args:
        painter: 目标 QPainter，函数内 save/restore 包裹状态修改。
        w: 绘制区域宽度。
        h: 绘制区域高度。
        indicator: 圆点主色。
        dot_size: 单个圆点尺寸，同时作为起伏偏移量单位。
        phase: 全局相位，取值 [0, 1)，驱动器周期 0.75s。

    Note:
        HeroUI 靠 wrapper 平移让圆点扎根，这里改为居中，由 _sway_y 的负向峰值偏移营造起伏。
    """
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
    """绘制 dots 变体：3 个圆点按相位错开做间歇闪烁。

    Args:
        painter: 目标 QPainter，函数内 save/restore 包裹状态修改。
        w: 绘制区域宽度。
        h: 绘制区域高度。
        indicator: 圆点主色，逐帧派生并改写透明度。
        dot_size: 单个圆点尺寸。
        phase: 全局相位，取值 [0, 1)，驱动器周期 1.4s。
    """
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


__all__ = ["N_DOTS", "paint_dots", "paint_wave"]
