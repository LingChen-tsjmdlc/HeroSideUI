"""Spinner 多变体动画驱动器。

提供一个简单的"线性循环 phase（0→1）"动画对象。所有 spinner 变体只需要
读取这个 phase，按变体语义自己计算每个子元素的位置/透明度即可——避免维护
多套 QPropertyAnimation。

driver.phase ∈ [0, 1)，无限循环、线性、duration 可配。

各变体的语义换算（在组件 paintEvent 里做）:

  default      | circle1 角度 = phase*360 (ease)；circle2 角度 = -phase*360 (linear)
                 → 用两个独立 driver
  simple       | 整体角度 = phase*360 (linear, 0.8s)
  gradient     | conical 起始角 = phase*360 (linear, 1.0s)
  spinner      | 12 bar，第 i 根 alpha = fade_out((phase - i*delay) % 1)
                 fade_out(t) = clamp(1 - t / 1.2 * 1.0, 0, 1) —— 线性淡出
                 总周期 1.2s
  wave         | 3 dot，dot[i] y_offset = -150% * sin(2π*((phase - i*step) % 1))
                 ease 750ms；HeroUI 用 cubic ease，但 sin 视感等价
  dots         | 3 dot，alpha = blink(phase - i*delay)
                 blink(t) = 0.2 + 0.8*( ramp(t) ); 0%→0.2 / 20%→1 / 100%→0.2
                 周期 1.4s
"""

from typing import Optional

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
)
from PySide6.QtWidgets import QWidget


class PhaseDriver(QObject):
    """线性循环 phase 驱动器（0 → 1，无限循环）。

    参数:
        owner: paintEvent 的 widget；phase 推进时调用 owner.update()
        duration: 单个周期时长（ms）
        easing: 缓动曲线，默认 Linear
    """

    def __init__(
        self,
        owner: QWidget,
        duration: int = 1200,
        easing: QEasingCurve.Type = QEasingCurve.Type.Linear,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent or owner)
        self._owner = owner
        self._phase = 0.0

        self._anim = QPropertyAnimation(self, b"phase")
        self._anim.setDuration(duration)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(easing)

    def _get_phase(self) -> float:
        return self._phase

    def _set_phase(self, v: float):
        self._phase = v
        self._owner.update()

    phase = Property(float, _get_phase, _set_phase)

    def value(self) -> float:
        """当前 phase ∈ [0, 1)。"""
        return self._phase

    def set_duration(self, ms: int):
        """运行中改 duration（重启动画以生效）。"""
        running = self.is_running()
        self._anim.stop()
        self._anim.setDuration(ms)
        if running:
            self._anim.start()

    def start(self):
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._phase = 0.0
            self._anim.start()

    def stop(self):
        self._anim.stop()

    def is_running(self) -> bool:
        return self._anim.state() == QPropertyAnimation.State.Running


__all__ = ["PhaseDriver"]
