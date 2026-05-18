"""variant=simple —— Tailwind 经典 loader。

HeroUI SVG 原版结构:
    <svg viewBox="0 0 24 24" fill="none">
      <circle cx=12 cy=12 r=10 stroke="currentColor" strokeWidth=4 opacity=0.25 />
      <path d="M4 12a8 8 0 018-8V0..." fill="currentColor" opacity=0.75 />
    </svg>
整体 animate-spin (1s linear infinite)
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen


def paint_simple(
    painter: QPainter,
    w: int,
    h: int,
    indicator: QColor,
    border: float,
    phase: float,
):
    """phase ∈ [0, 1)；驱动器周期 1.0s。"""
    side = min(w, h) - 2  # 留 1px 抗锯齿边
    cx = w / 2
    cy = h / 2

    painter.save()
    painter.translate(cx, cy)
    painter.rotate(phase * 360.0)

    # 半径按 24px viewBox 等比缩放，笔触使用配置的 border_width
    scale = side / 24.0
    r = 10.0 * scale
    stroke_w = border

    rect = QRectF(-r, -r, r * 2, r * 2)

    # ---- 25% 透明的整圈 ----
    bg = QColor(indicator)
    bg.setAlphaF(0.25)
    pen = QPen(bg, stroke_w)
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(rect)

    # ---- 75% 透明的 1/4 实心扇形 (对应原 path) ----
    # path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4..."
    # 简化为：在外圆 (r+stroke/2) 与内圆 (r-stroke/2) 之间画约 90° 的环段
    fg = QColor(indicator)
    fg.setAlphaF(0.75)
    outer_r = r + stroke_w / 2
    inner_r = r - stroke_w / 2

    # 起点 12 点钟方向（path 从 (4, 12) 起算）→ 12 点 = -90°
    # 沿顺时针 90° → 到 3 点钟
    path = QPainterPath()
    outer_rect = QRectF(-outer_r, -outer_r, outer_r * 2, outer_r * 2)
    inner_rect = QRectF(-inner_r, -inner_r, inner_r * 2, inner_r * 2)
    # Qt: 起点 3 点钟，逆时针正角；想从 12 点 (-90°) 开始顺时针 90° → start=180, span=-90
    path.arcMoveTo(outer_rect, 180)
    path.arcTo(outer_rect, 180, -90)
    path.arcTo(inner_rect, 90, 90)
    path.closeSubpath()

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(fg)
    painter.drawPath(path)

    painter.restore()


__all__ = ["paint_simple"]
