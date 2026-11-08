"""提供透明度与缩放联动的浮层过渡。"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    Signal,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class FadeScaleAnimation(QObject):
    """同步浮层的透明度和缩放进度。

    Attributes:
        progress: 0 到 1 的当前进度。
        finished_in: 入场完成信号。
        finished_out: 退场完成信号。
    """

    finished_in = Signal()
    finished_out = Signal()

    def __init__(
        self,
        target: QWidget,
        scale_min: float = 0.95,
        duration_in: int = 150,
        duration_out: int = 150,
        easing_in: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
        easing_out: QEasingCurve.Type = QEasingCurve.Type.InCubic,
        apply_opacity_via: str = "window",
        parent: QObject | None = None,
    ):
        """初始化浮层过渡。

        Args:
            target: 接受透明度设置和重绘请求的控件。
            scale_min: 进度为 0 时的缩放比例。
            duration_in: 入场毫秒数。
            duration_out: 退场毫秒数。
            easing_in: 入场曲线。
            easing_out: 退场曲线。
            apply_opacity_via: window 设置窗口透明度，effect 安装透明度效果，manual 交由调用者绘制。
            parent: Qt 父对象；省略时使用 target。
        """
        super().__init__(parent or target)
        self._target = target
        self._scale_min = scale_min
        self._duration_in = duration_in
        self._duration_out = duration_out
        self._easing_in = easing_in
        self._easing_out = easing_out
        self._opacity_mode = apply_opacity_via

        self._progress = 0.0
        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setEasingCurve(self._easing_in)
        self._anim.finished.connect(self._on_finished)

        self._direction: str | None = None

        self._effect: QGraphicsOpacityEffect | None = None
        if apply_opacity_via == "effect":
            self._effect = QGraphicsOpacityEffect(target)
            self._effect.setOpacity(0.0)
            target.setGraphicsEffect(self._effect)

    def _get_progress(self) -> float:
        """返回当前过渡进度。"""
        return self._progress

    def _set_progress(self, v: float):
        """设置过渡进度并应用当前外观。"""
        self._progress = v
        self._apply()

    progress = Property(float, _get_progress, _set_progress)

    def play_in(self, instant: bool = False):
        """从当前进度进入。

        Args:
            instant: 是否直接应用入场终态并发出完成信号。
        """
        self._direction = "in"
        self._anim.stop()
        if instant:
            self._progress = 1.0
            self._apply()
            self.finished_in.emit()
            return
        self._anim.setEasingCurve(self._easing_in)
        self._anim.setDuration(self._duration_in)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def play_out(self, instant: bool = False):
        """从当前进度退出。

        Args:
            instant: 是否直接应用退场终态并发出完成信号。
        """
        self._direction = "out"
        self._anim.stop()
        if instant:
            self._progress = 0.0
            self._apply()
            self.finished_out.emit()
            return
        self._anim.setEasingCurve(self._easing_out)
        self._anim.setDuration(self._duration_out)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def is_running(self) -> bool:
        """返回过渡是否正在运行。"""
        return self._anim.state() == QPropertyAnimation.State.Running

    def progress_value(self) -> float:
        """返回当前过渡进度。"""
        return self._progress

    def opacity_value(self) -> float:
        """返回当前透明度。"""
        return self._progress

    def scale_value(self) -> float:
        """返回由进度换算的缩放比例。"""
        return self._scale_min + (1.0 - self._scale_min) * self._progress

    def _apply(self):
        """按透明度模式应用当前进度并请求重绘。"""
        opacity = self._progress
        if self._opacity_mode == "window":
            self._target.setWindowOpacity(opacity)
        elif self._opacity_mode == "effect" and self._effect is not None:
            self._effect.setOpacity(opacity)

        self._target.update()

    def _on_finished(self):
        """按方向发出入场或退场完成信号。"""
        if self._direction == "in":
            self.finished_in.emit()
        elif self._direction == "out":
            self.finished_out.emit()
        self._direction = None
