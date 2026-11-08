"""spinner 变体：iOS 风格 12 根时钟刻度，逐根相位差线性淡出。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
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
    """绘制 spinner 变体：12 根时钟刻度按相位差逐根淡出。

    Args:
        painter: 目标 QPainter，函数内平移旋转并以 save/restore 包裹。
        w: 绘制区域宽度。
        h: 绘制区域高度。
        indicator: 主色，每根刻度逐帧派生并改写透明度。
        bar_length: 刻度棒长度，同时决定内圆留空半径。
        bar_width: 刻度棒宽度，同时作为圆角半径。
        phase: 全局相位，取值 [0, 1)，驱动器周期 1.2s。

    Note:
        相位差固定为 1/12，i 越大越晚出现以形成旋转方向感；透明度由 1 线性淡到 0.15。
    """
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


__all__ = ["N_BARS", "paint_spinner"]
