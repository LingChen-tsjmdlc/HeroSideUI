"""gradient 变体：QConicalGradient 透明→主色，内圆挖空留环。"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QPainter,
    QPainterPath,
)


def paint_gradient(
    painter: QPainter,
    w: int,
    h: int,
    indicator: QColor,
    border: float,
    phase: float,
):
    """绘制 gradient 变体：锥形渐变圆环，头部实色、拖尾淡出到透明。

    Args:
        painter: 目标 QPainter，函数内改写画笔与画刷。
        w: 绘制区域宽度。
        h: 绘制区域高度。
        indicator: 主色，头部实色与透明端都由它派生。
        border: 圆环线宽，用于计算内圆半径。
        phase: 全局相位，取值 [0, 1)，驱动器周期 1.0s。

    Note:
        圆环由 QPainterPath 的 even-odd 填充规则挖空；外半径不大于内半径时直接返回，不做绘制。
    """
    side = min(w, h)
    cx = w / 2
    cy = h / 2
    outer_r = side / 2 - 1  # 留 1px 抗锯齿边
    inner_r = max(0.5, outer_r - border)

    if outer_r <= inner_r:
        return

    # 1) 外圆区裁剪到圆环（用 QPainterPath 的 even-odd）
    ring = QPainterPath()
    ring.setFillRule(Qt.FillRule.OddEvenFill)
    ring.addEllipse(QPointF(cx, cy), outer_r, outer_r)
    ring.addEllipse(QPointF(cx, cy), inner_r, inner_r)

    # 2) Conical gradient — 头部实色，沿"已经走过"的方向（拖尾）淡出到透明，
    #    头部前方（尚未走到）保持透明。
    #
    # QConicalGradient 起始角 90° = 12 点钟；从起始角沿逆时针扫描 0→1。
    # 顺时针推进 = 起始角递减（phase 增 → 起始角减 → 头部从 12→3→6→9）。
    # 顺时针前进时，"刚走过"的尾巴 = 头部 → 起始角的逆时针方向 = QConical 扫描方向。
    # 所以 0.0 处放实色（头），扫描到 ~0.4（即拖尾走完 144°）时淡为透明，
    # 之后到 1.0 都保持透明（包括头部前方）。
    grad = QConicalGradient(QPointF(cx, cy), 90.0 - phase * 360.0)
    transparent = QColor(indicator)
    transparent.setAlpha(0)
    grad.setColorAt(0.0, QColor(indicator))  # 头部：实色
    grad.setColorAt(0.4, transparent)  # 拖尾末端：完全透明
    grad.setColorAt(1.0, transparent)  # 前方：透明

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(grad))
    painter.drawPath(ring)


__all__ = ["paint_gradient"]
