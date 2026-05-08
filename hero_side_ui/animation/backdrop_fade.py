"""
BackdropFade —— 遮罩层淡入淡出动画

通用遮罩渐入渐出控制器，供 Popover / Modal / Drawer 等浮层组件的
backdrop 子 widget 复用。

核心能力:
  - 通过 Qt Property `progress`（0→1）驱动整体透明度
  - owner 的 paintEvent 读 `progress_value()`，用 `painter.setOpacity()`
    实现淡入淡出（painter 自绘场景）
  - 支持独立的进/出时长与曲线
  - play_out 动画结束时自动 hide，避免 owner 手动管生命周期

典型用法::

    class MyBackdrop(QWidget):
        def __init__(self, ...):
            super().__init__(...)
            self._fade = BackdropFade(
                owner=self, duration_in=260, duration_out=200,
            )

        def paintEvent(self, event):
            p = QPainter(self)
            p.setOpacity(self._fade.progress_value())
            ...

    # 显示：
    backdrop.show()
    backdrop._fade.play_in()
    # 关闭：
    backdrop._fade.play_out()  # 动画结束自动 hide
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    QObject, QPropertyAnimation, QEasingCurve, Property,
)
from typing import Optional


class BackdropFade(QObject):
    """遮罩层渐入渐出动画驱动器。

    参数:
        owner: 遮罩 widget 本体（动画结束后会被 hide）
        duration_in: 渐入时长 (ms)
        duration_out: 渐出时长 (ms)
        easing: 缓动曲线（默认 OutCubic）
        auto_hide_on_out: play_out 结束后是否自动 hide owner
    """

    def __init__(
        self,
        owner: QWidget,
        duration_in: int = 260,
        duration_out: int = 200,
        easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
        auto_hide_on_out: bool = True,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent or owner)
        self._owner = owner
        self._duration_in = duration_in
        self._duration_out = duration_out
        self._easing = easing
        self._auto_hide = auto_hide_on_out

        self._progress = 0.0
        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setEasingCurve(self._easing)
        self._anim.finished.connect(self._on_finished)

    # ---- Qt property: progress ----
    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, v: float):
        self._progress = v
        self._owner.update()

    progress = Property(float, _get_progress, _set_progress)

    def progress_value(self) -> float:
        return self._progress

    # ---- 播放控制 ----
    def play_in(self):
        self._anim.stop()
        self._anim.setDuration(self._duration_in)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def play_out(self):
        self._anim.stop()
        self._anim.setDuration(self._duration_out)
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_finished(self):
        if self._auto_hide and self._progress <= 0.01:
            self._owner.hide()
