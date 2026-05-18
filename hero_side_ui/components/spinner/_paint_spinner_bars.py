"""variant=spinner —— iOS UIActivityIndicator 风格的 12 根时钟刻度。

HeroUI 原版 CSS:
    每根 i:
      transform: rotate(30deg * --bar-index) translate(140%);
      animation: fade-out 1.2s linear infinite;
      animation-delay: calc(-1.2s + 0.1s * --bar-index);
    @keyframes fade-out { 0%{opacity:1} 100%{opacity:0.15} }  (大致)

复刻策略:
    用一个 1.2s phase 驱动；第 i 根的局部 phase = (phase + i*delay) % 1
    其中 delay = 1/12 ≈ 0.0833（让它走 0~1 的循环）
    透明度 = 1 - phase_local（线性淡出，min 0.15）
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter


N_BARS = 12
DELAY = 1.0 / N_BARS  # 每根之间的相位差


def paint_spinner(
    painter: QPainter,
    w: int,
    h: int,
    indicator: QColor,
    bar_length: float,
    bar_width: float,
    phase: float,
):
    """phase ∈ [0, 1)；驱动器周期 1.2s。"""
    side = min(w, h)
    cx = w / 2
    cy = h / 2
    outer_r = side / 2.0
    # bar 内端到圆心的距离：留出中间一个内圆
    inner_r = max(1.0, outer_r - bar_length)

    painter.save()
    painter.translate(cx, cy)
    painter.setPen(Qt.PenStyle.NoPen)

    for i in range(N_BARS):
        # 相位：i 越大越晚出现 → 旋转方向感
        local = (phase + i * DELAY) % 1.0
        # fade-out：1 → 0.15 线性
        alpha = 1.0 - local * (1.0 - 0.15)
        c = QColor(indicator)
        c.setAlphaF(alpha)

        painter.save()
        painter.rotate(i * 30.0)
        painter.setBrush(c)
        # 在 12 点钟方向画一根胶囊棒：中心 y = -(inner_r + bar_length/2)
        y_center = -(inner_r + bar_length / 2.0)
        rect = QRectF(
            -bar_width / 2.0,
            y_center - bar_length / 2.0,
            bar_width,
            bar_length,
        )
        painter.drawRoundedRect(rect, bar_width / 2.0, bar_width / 2.0)
        painter.restore()

    painter.restore()


__all__ = ["paint_spinner", "N_BARS"]
