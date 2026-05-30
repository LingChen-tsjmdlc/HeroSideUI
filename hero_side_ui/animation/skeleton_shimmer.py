"""HeroUI 风格 Skeleton shimmer（扫光）动画

用 QPropertyAnimation 驱动 0.0 → 1.0 循环 progress，
owner 在 paintEvent 里用 progress 绘制从左到右移动的渐变亮带。

参数:
    owner: 拥有这个动画的控件
    duration: 一个完整扫光周期(ms)，默认 1500

用法::

    self._shimmer = SkeletonShimmerAnimation(self, duration=1500)
    self._shimmer.start()
    # paintEvent:
    progress = self._shimmer.progress_value()
    # 用 progress 绘制渐变亮带
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import (
    QObject,
    QPropertyAnimation,
    QEasingCurve,
    Property,
)
from PySide6.QtWidgets import QWidget


class SkeletonShimmerAnimation(QObject):
    """循环扫光动画，驱动 0.0→1.0 的 progress 值。"""

    def __init__(
        self,
        owner: QWidget,
        duration: int = 1500,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent or owner)
        self._owner = owner
        self._progress = 0.0

        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(duration)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        # 官方: animate-shimmer 2s infinite (默认 ease 缓动)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, v: float):
        self._progress = v
        self._owner.update()

    progress = Property(float, _get_progress, _set_progress)

    def progress_value(self) -> float:
        return self._progress

    def start(self):
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._anim.start()

    def stop(self):
        self._anim.stop()

    def is_running(self) -> bool:
        return self._anim.state() == QPropertyAnimation.State.Running
