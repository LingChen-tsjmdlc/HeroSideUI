"""提供对勾的分段绘制和可取消的延迟描勾控制。"""

from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QPainter, QPen

__all__ = ["CheckDrawAnimation", "paint_animated_check"]


_A = (4.5, 12.75)
_B = (10.5, 18.75)
_C = (19.5, 5.25)


def paint_animated_check(
    painter: QPainter,
    rect: QRect | QRectF | tuple,
    color: QColor,
    progress: float,
    *,
    opacity: float = 1.0,
    stroke_width: float | None = None,
) -> None:
    """按路径进度绘制对勾，不改变调用者的画笔状态。

    Args:
        painter: 已经开始绘制的 QPainter。
        rect: 绘制区域，可为 QRect、QRectF 或四元组。
        color: 描边颜色。
        progress: 描绘进度，限制在 0 到 1。
        opacity: 与现有画笔透明度叠加的系数。
        stroke_width: 描边像素宽度；省略时根据区域大小计算。
    """
    p = max(0.0, min(1.0, float(progress)))
    if p <= 0.001:
        return

    if isinstance(rect, (QRect, QRectF)):
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    else:
        x, y, w, h = rect
    x, y, w, h = float(x), float(y), float(w), float(h)

    sx = w / 24.0
    sy = h / 24.0
    ax, ay = x + _A[0] * sx, y + _A[1] * sy
    bx, by = x + _B[0] * sx, y + _B[1] * sy
    cx, cy = x + _C[0] * sx, y + _C[1] * sy

    len_ab = math.hypot(bx - ax, by - ay)
    len_bc = math.hypot(cx - bx, cy - by)
    total = len_ab + len_bc
    if total <= 0.0:
        return

    target = total * p

    painter.save()
    painter.setOpacity(painter.opacity() * opacity)

    if stroke_width is None:
        stroke_width = max(1.5, 3.0 * min(sx, sy))
    pen = QPen(color, stroke_width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    if target <= len_ab:
        t = target / len_ab if len_ab > 0 else 0
        end_x = ax + (bx - ax) * t
        end_y = ay + (by - ay) * t
        painter.drawLine(QPointF(ax, ay), QPointF(end_x, end_y))
    else:
        painter.drawLine(QPointF(ax, ay), QPointF(bx, by))
        remaining = target - len_ab
        t = remaining / len_bc if len_bc > 0 else 0
        end_x = bx + (cx - bx) * t
        end_y = by + (cy - by) * t
        painter.drawLine(QPointF(bx, by), QPointF(end_x, end_y))

    painter.restore()


class CheckDrawAnimation(QObject):
    """管理描勾进度、选中延迟和取消方式。

    Attributes:
        progress: 0 到 1 的当前描绘进度。
    """

    def __init__(
        self,
        target: QObject,
        *,
        on_step: Callable[[float], None] | None = None,
        duration_in: int = 500,
        duration_out: int = 200,
        delay_in: int = 100,
        easing_in: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
        easing_out: QEasingCurve.Type = QEasingCurve.Type.InCubic,
        draw_out: bool = False,
    ):
        """初始化对勾控制器。

        Args:
            target: 拥有控制器的 QObject。
            on_step: 进度变化时执行的回调。
            duration_in: 描出对勾的毫秒数。
            duration_out: 反向擦除的毫秒数。
            delay_in: 选中后开始描勾前的延迟毫秒数。
            easing_in: 描出时的曲线。
            easing_out: 擦除时的曲线。
            draw_out: 取消时是否反向擦除；False 时保留完整对勾供外部淡出。
        """
        super().__init__(target)
        self._target = target
        self._on_step = on_step
        self._duration_in = duration_in
        self._duration_out = duration_out
        self._delay_in = delay_in
        self._easing_in = easing_in
        self._easing_out = easing_out
        self._draw_out = draw_out

        self._progress = 0.0
        self._anim = QPropertyAnimation(self, b"progress")
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._start_in_anim)
        self._pending_target = None

    def _get_progress(self) -> float:
        """返回当前描绘进度。"""
        return self._progress

    def _set_progress(self, v: float):
        """设置描绘进度并通知回调。"""
        v = max(0.0, min(1.0, float(v)))
        if v == self._progress:
            return
        self._progress = v
        if self._on_step is not None:
            self._on_step(v)

    progress = Property(float, _get_progress, _set_progress)

    def play(self, checked: bool):
        """取消旧请求，按选中状态描出或擦除对勾。

        Args:
            checked: True 时延迟描出；False 时按 draw_out 策略退出。
        """
        self._anim.stop()
        self._delay_timer.stop()
        self._pending_target = checked

        if checked:
            self._set_progress(0.0)
            self._pending_target = True
            if self._delay_in > 0:
                self._delay_timer.start(self._delay_in)
            else:
                self._start_in_anim()
        else:
            if self._draw_out:
                start = self._progress
                self._anim.setStartValue(start)
                self._anim.setEndValue(0.0)
                self._anim.setDuration(self._duration_out)
                self._anim.setEasingCurve(self._easing_out)
                self._anim.start()
            else:
                self._set_progress(1.0)

    def set_immediate(self, checked: bool):
        """取消待执行请求并立即设置终态。

        Args:
            checked: True 对应完整对勾，False 对应空白。
        """
        self._anim.stop()
        self._delay_timer.stop()
        self._pending_target = None
        self._set_progress(1.0 if checked else 0.0)

    def stop(self):
        """停止动画和延迟任务，保留当前进度。"""
        self._anim.stop()
        self._delay_timer.stop()
        self._pending_target = None

    def _start_in_anim(self):
        """仅为仍有效的选中请求启动描勾。"""
        if self._pending_target is not True:
            return
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self._duration_in)
        self._anim.setEasingCurve(self._easing_in)
        self._anim.start()
