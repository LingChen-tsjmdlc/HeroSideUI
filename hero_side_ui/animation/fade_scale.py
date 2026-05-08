"""
HeroUI 风格的"淡入 + 缩放"动画 (Fade + Scale)

通用打开/关闭过渡：opacity 0→1 + scale 0.95→1，150ms OutCubic。
适用于 Popover / Modal / Dropdown / Tooltip 等浮层组件。

实现方式:
  - 用一个 0..1 的 progress（QPropertyAnimation 驱动）
  - opacity = progress
  - scale = scale_min + (1 - scale_min) * progress
  - 由 owner 控件在 paintEvent 中读取 scale_value() 自己做 QPainter.scale()
  - opacity 由 setWindowOpacity（顶层窗口）或 QGraphicsOpacityEffect（子控件）实现

用法 1: 顶层窗口（如 Popover）::

    self._fade = FadeScaleAnimation(target=self,
                                    apply_opacity_via="window")
    self._fade.opened.connect(self._on_open_finished)
    self._fade.closed.connect(self._on_close_finished)
    # 打开
    self._fade.play_in()
    # 在 paintEvent 里:
    s = self._fade.scale_value()
    if s < 1.0:
        painter.translate(cx, cy); painter.scale(s, s); painter.translate(-cx, -cy)

用法 2: 普通子控件::

    self._fade = FadeScaleAnimation(target=widget,
                                    apply_opacity_via="effect")
    self._fade.play_in()    # 出现
    self._fade.play_out()   # 隐藏
"""

from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import (
    QObject, QPropertyAnimation, QEasingCurve, Property, Signal,
)
from typing import Optional


class FadeScaleAnimation(QObject):
    """淡入淡出 + 缩放联动动画。

    参数:
        target: 目标控件
        scale_min: 起始缩放比例（0~1），默认 0.95
        duration_in: 打开动画时长(ms)，默认 150
        duration_out: 关闭动画时长(ms)，默认 150
        easing_in / easing_out: 进出曲线，默认 OutCubic / InCubic
        apply_opacity_via:
            - "window"   → 用 setWindowOpacity（顶层窗口推荐）
            - "effect"   → 用 QGraphicsOpacityEffect（子控件）
            - "manual"   → 不自动管 opacity，由调用者读取 progress 自处理

    信号:
        finished_in:  play_in 完成
        finished_out: play_out 完成
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
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent or target)
        self._target = target
        self._scale_min = scale_min
        self._duration_in = duration_in
        self._duration_out = duration_out
        self._easing_in = easing_in
        self._easing_out = easing_out
        self._opacity_mode = apply_opacity_via

        # progress 0..1
        self._progress = 0.0
        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setEasingCurve(self._easing_in)
        self._anim.finished.connect(self._on_finished)

        # 内部状态：当前播放方向 ("in" / "out" / None)
        self._direction: Optional[str] = None

        # 子控件模式下复用 GraphicsOpacityEffect
        self._effect: Optional[QGraphicsOpacityEffect] = None
        if apply_opacity_via == "effect":
            self._effect = QGraphicsOpacityEffect(target)
            self._effect.setOpacity(0.0)
            target.setGraphicsEffect(self._effect)

    # ---- Qt property: progress ----
    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, v: float):
        self._progress = v
        self._apply()

    progress = Property(float, _get_progress, _set_progress)

    # ---- public ----
    def play_in(self, instant: bool = False):
        """从当前 progress 推进到 1.0（淡入 + 放大到原尺寸）。"""
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
        """从当前 progress 推进到 0.0（淡出 + 缩小）。"""
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
        return self._anim.state() == QPropertyAnimation.State.Running

    def progress_value(self) -> float:
        return self._progress

    def opacity_value(self) -> float:
        return self._progress

    def scale_value(self) -> float:
        return self._scale_min + (1.0 - self._scale_min) * self._progress

    # ---- internal ----
    def _apply(self):
        opacity = self._progress
        if self._opacity_mode == "window":
            self._target.setWindowOpacity(opacity)
        elif self._opacity_mode == "effect" and self._effect is not None:
            self._effect.setOpacity(opacity)
        # 触发 owner 重绘以更新 scale
        self._target.update()

    def _on_finished(self):
        if self._direction == "in":
            self.finished_in.emit()
        elif self._direction == "out":
            self.finished_out.emit()
        self._direction = None
