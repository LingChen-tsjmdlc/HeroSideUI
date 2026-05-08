"""
HeroUI 风格的"未定态"循环动画 (Indeterminate)

包含两类常用 loading 动画:
  - IndeterminateBarAnimation: 线性条上滑块来回循环（用于 Progress.is_indeterminate）
  - SpinAnimation: 0→360 的旋转角度循环（用于 CircularProgress.is_indeterminate / Spinner）

二者都暴露一个 0..1 或 0..360 的实时值，由 owner 在 paintEvent 里读取自绘。

用法 1 — 线性滑块::

    self._loader = IndeterminateBarAnimation(self)
    self._loader.start()
    # paintEvent:
    pos = self._loader.position()  # ∈ [-bar_width_ratio, 1.0]
    # 画 bar，用 pos 作为左侧 ratio

用法 2 — 旋转::

    self._spin = SpinAnimation(self, duration=900)
    self._spin.start()
    # paintEvent:
    deg = self._spin.angle()
    painter.translate(cx, cy); painter.rotate(deg); painter.translate(-cx, -cy)
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    QObject, QPropertyAnimation, QEasingCurve, Property,
)
from typing import Optional


class IndeterminateBarAnimation(QObject):
    """线性进度条的"未定态"滑块动画。

    驱动一个 [-bar_ratio, 1.0] 之间循环的 position 值，
    owner 在 paintEvent 中根据它定位滑块。

    参数:
        owner: 拥有这个动画的控件（动画驱动 owner.update()）
        duration: 一个完整周期时长(ms)，默认 1500
        bar_ratio: 滑块宽度占总长比例，默认 0.4
        easing: 缓动曲线，默认 InOutSine（HeroUI 体感）
    """

    def __init__(
        self,
        owner: QWidget,
        duration: int = 1500,
        bar_ratio: float = 0.4,
        easing: QEasingCurve.Type = QEasingCurve.Type.InOutSine,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent or owner)
        self._owner = owner
        self._bar_ratio = bar_ratio
        self._position = -bar_ratio

        self._anim = QPropertyAnimation(self, b"position")
        self._anim.setDuration(duration)
        self._anim.setStartValue(-bar_ratio)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(easing)

    def _get_pos(self) -> float:
        return self._position

    def _set_pos(self, v: float):
        self._position = v
        self._owner.update()

    position = Property(float, _get_pos, _set_pos)

    def bar_ratio(self) -> float:
        return self._bar_ratio

    def start(self):
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._position = -self._bar_ratio
            self._anim.start()

    def stop(self):
        self._anim.stop()

    def is_running(self) -> bool:
        return self._anim.state() == QPropertyAnimation.State.Running


class SpinAnimation(QObject):
    """0→360° 的循环旋转动画。

    参数:
        owner: 拥有这个动画的控件
        duration: 一圈时长(ms)，默认 900
        easing: 缓动曲线，默认 Linear
    """

    def __init__(
        self,
        owner: QWidget,
        duration: int = 900,
        easing: QEasingCurve.Type = QEasingCurve.Type.Linear,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent or owner)
        self._owner = owner
        self._angle = 0.0

        self._anim = QPropertyAnimation(self, b"angle")
        self._anim.setDuration(duration)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(360.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(easing)

    def _get_angle(self) -> float:
        return self._angle

    def _set_angle(self, v: float):
        self._angle = v
        self._owner.update()

    angle = Property(float, _get_angle, _set_angle)

    def angle_value(self) -> float:
        return self._angle

    def start(self):
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._anim.start()

    def stop(self):
        self._anim.stop()

    def is_running(self) -> bool:
        return self._anim.state() == QPropertyAnimation.State.Running
