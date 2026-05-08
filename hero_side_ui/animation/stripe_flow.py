"""
HeroUI 风格的"斜纹流动"动画 (Stripe Flow)

驱动一个 0..period 的 offset 循环值，owner 在 paintEvent 里
用 `offset % period` 作为斜纹起点 x 平移量。

适用于:
  - Progress.is_striped 流动条带
  - 任意需要"匀速向右流动的图案"的场景

参数:
    owner: 拥有这个动画的控件
    period: 一个流动周期对应的像素数（默认 32 = 16px stripe × 2）
    duration: 一个周期时长(ms)，默认 1000

用法::

    self._flow = StripeFlowAnimation(self, period=32, duration=1000)
    self._flow.start()
    # paintEvent:
    offset = self._flow.offset() % period
    # 用 offset 平移条带起点
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    QObject, QPropertyAnimation, QEasingCurve, Property,
)
from typing import Optional


class StripeFlowAnimation(QObject):
    def __init__(
        self,
        owner: QWidget,
        period: float = 32.0,
        duration: int = 1000,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent or owner)
        self._owner = owner
        self._period = period
        self._offset = 0.0

        self._anim = QPropertyAnimation(self, b"offset")
        self._anim.setDuration(duration)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(period)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, v: float):
        self._offset = v
        self._owner.update()

    offset = Property(float, _get_offset, _set_offset)

    def period(self) -> float:
        return self._period

    def offset_value(self) -> float:
        return self._offset

    def start(self):
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._anim.start()

    def stop(self):
        self._anim.stop()

    def is_running(self) -> bool:
        return self._anim.state() == QPropertyAnimation.State.Running
