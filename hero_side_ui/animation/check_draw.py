"""
Check draw animation - 手绘勾选标记动画
======================================

把 Checkbox 的"按路径描出对勾"动画抽出来，供 Checkbox / Listbox / Switch /
未来的 Select 选中态等任何"打勾视觉反馈"组件复用。

API
---

- :func:`paint_animated_check(painter, rect, color, progress, *, opacity=1.0,
  stroke_width=None)` — **纯绘制函数**。在指定矩形里按 ``progress (0~1)``
  画出对勾的"前 progress 段"。0 = 不画，1 = 完整对勾。

- :class:`CheckDrawAnimation(target, ...)` — **驱动器**。封装 progress 0↔1
  的 ``QPropertyAnimation``，处理"勾选立即清零→延迟 100ms 再描出"和"取消
  立即置 1 让对勾随其他视觉淡出"两种典型节奏。``progress`` 通过 Qt Property
  暴露 / 直接读取（``CheckDrawAnimation.progress``）。

对勾路径（24×24 viewBox）::

    A(4.5, 12.75) --AB(短下斜)--> B(10.5, 18.75) --BC(长上斜)--> C(19.5, 5.25)

笔宽参考 SVG ``stroke-width=3`` 等比缩放，最小 1.5px；圆头圆角接合。

简单示例 — 直接绘制::

    from hero_side_ui.animation import paint_animated_check

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        paint_animated_check(p, self.rect(), QColor("#FFFFFF"),
                             progress=self._check_t, opacity=1.0)

简单示例 — 让 helper 管动画::

    from hero_side_ui.animation import CheckDrawAnimation

    self._check_anim = CheckDrawAnimation(
        self,
        on_step=lambda v: self.update(),  # 每帧 repaint
        duration_in=500,
        duration_out=200,
        delay_in=100,
    )

    def _on_selected_changed(self, checked: bool):
        self._check_anim.play(checked)

    def paintEvent(self, e):
        p = QPainter(self)
        paint_animated_check(p, icon_rect, color, self._check_anim.progress)
"""

from __future__ import annotations

import math
from typing import Callable, Optional, Union

from PySide6.QtCore import (
    Qt,
    QObject,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    Property,
    QPointF,
    QRect,
    QRectF,
)
from PySide6.QtGui import QColor, QPainter, QPen


__all__ = ["paint_animated_check", "CheckDrawAnimation"]


# 对勾路径锚点（24×24 viewBox）
_A = (4.5, 12.75)
_B = (10.5, 18.75)
_C = (19.5, 5.25)


def paint_animated_check(
    painter: QPainter,
    rect: Union[QRect, QRectF, tuple],
    color: QColor,
    progress: float,
    *,
    opacity: float = 1.0,
    stroke_width: Optional[float] = None,
) -> None:
    """按 ``progress`` 在 ``rect`` 区域内画出对勾的"前 progress 段"。

    Args:
        painter: 已 begin 的 QPainter。函数内部 save/restore，不影响外部状态。
        rect: 绘制矩形，可传 ``QRect`` / ``QRectF`` 或 ``(x, y, w, h)`` 元组。
        color: 笔的颜色。
        progress: 0.0 ~ 1.0，描边进度。0 = 不画，1 = 完整对勾。
        opacity: 整体透明度叠加（用于配合外部 fade 动画淡出）。
        stroke_width: 笔宽 (px)。为 ``None`` 时按 ``stroke=3`` (24×24 viewBox)
            等比缩放，最小 1.5px。
    """
    p = max(0.0, min(1.0, float(progress)))
    if p <= 0.001:
        return

    # 解析 rect → x, y, w, h（float）
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
    """驱动 progress 0↔1 的 helper。

    勾选 (``play(True)``)::
        立即把 progress 置 0（让对勾从头开始描），延迟 ``delay_in`` ms 后
        启动 0→1 的 ``QPropertyAnimation``，时长 ``duration_in``。
        (Checkbox 这套节奏让 fill 先铺开、再描勾，体感更顺滑)。

    取消 (``play(False)``)::
        默认行为：立即把 progress 置 1（整条对勾可见），然后让外部其他视觉
        （如 fill opacity / 整体淡出）把它"擦掉"。该模式下不真的播 1→0。
        如需"反向把对勾擦掉"，传 ``draw_out=True``：会启动 1→0 的动画。

    使用方式::

        self._check = CheckDrawAnimation(
            self,
            on_step=lambda v: self.update(),
            duration_in=500, delay_in=100, duration_out=200,
        )
        self._check.play(True)   # 勾选
        self._check.play(False)  # 取消
        # paintEvent 里：
        paint_animated_check(p, rect, color, self._check.progress)
    """

    def __init__(
        self,
        target: QObject,
        *,
        on_step: Optional[Callable[[float], None]] = None,
        duration_in: int = 500,
        duration_out: int = 200,
        delay_in: int = 100,
        easing_in: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
        easing_out: QEasingCurve.Type = QEasingCurve.Type.InCubic,
        draw_out: bool = False,
    ):
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
        self._pending_target = None  # 延迟期间记录目标，避免脏数据

    # ---- Qt Property ----
    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, v: float):
        v = max(0.0, min(1.0, float(v)))
        if v == self._progress:
            return
        self._progress = v
        if self._on_step is not None:
            self._on_step(v)

    progress = Property(float, _get_progress, _set_progress)

    # ---- 控制 ----
    def play(self, checked: bool):
        """根据 ``checked`` 状态切换 progress。

        - ``True`` → 立即清零，延迟 ``delay_in`` 后描出 0→1
        - ``False`` →
              ``draw_out=False`` (默认): 立即置 1（外部其他视觉负责擦掉）
              ``draw_out=True``       : 播 1→0
        """
        self._anim.stop()
        self._delay_timer.stop()

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
                # 立即可见，外部 fade 把它擦掉
                self._set_progress(1.0)

    def set_immediate(self, checked: bool):
        """跳过动画直接设 progress=0/1（disable_animation 场景）。"""
        self._anim.stop()
        self._delay_timer.stop()
        self._set_progress(1.0 if checked else 0.0)

    def stop(self):
        """终止所有动画（保留当前 progress）。"""
        self._anim.stop()
        self._delay_timer.stop()

    def _start_in_anim(self):
        # 延迟到点：若期间又被 play(False)，pending_target 已被改 / stop 已 stop
        if self._pending_target is not True:
            return
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self._duration_in)
        self._anim.setEasingCurve(self._easing_in)
        self._anim.start()
