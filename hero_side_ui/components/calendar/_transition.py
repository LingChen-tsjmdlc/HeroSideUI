"""Calendar 翻页滑动：旧网格截图覆盖层滑出、新网格底层滑入。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPropertyAnimation
from PySide6.QtWidgets import QLabel, QWidget

from ...animation import stop_tween, tween_property
from ...utils import safe_delete

_DURATION_MS = 250


class _SlideTransition:
    """管理单个网格容器的翻页滑动。宿主需提供一个固定尺寸的 viewport widget。"""

    def __init__(self, viewport: QWidget, content: QWidget) -> None:
        """创建滑动过渡管理器。

        Args:
            viewport: 固定尺寸的视口 widget。
            content: 被滑动的网格内容 widget。
        """
        self._viewport = viewport
        self._content = content
        self._overlay: QLabel | None = None
        self._anim_in: QPropertyAnimation | None = None
        self._anim_out: QPropertyAnimation | None = None

    def is_active(self) -> bool:
        """当前是否正在播放过渡。

        Returns:
            旧网格截图覆盖层存在时为 True。
        """
        return self._overlay is not None

    def run(self, direction: int, on_render_new) -> None:
        """播放一次翻页滑动。

        Args:
            direction: +1 向后翻（新网格从右侧滑入），-1 向前翻。
            on_render_new: 渲染新网格内容的回调，在覆盖层就位后调用。

        Note:
            先把旧网格截图盖在上层，再渲染新内容并把新网格移到屏外，
            随后两条 tween 同时把新网格滑入、旧截图滑出；
            视口尺寸未定（<=0）时直接渲染，跳过动画。
        """
        width = self._viewport.width()
        height = self._viewport.height()
        self._finish()
        if width <= 0 or height <= 0:
            on_render_new()
            return
        overlay = QLabel(self._viewport)
        overlay.setPixmap(self._content.grab())
        overlay.setGeometry(self._content.geometry())
        overlay.show()
        overlay.raise_()
        self._overlay = overlay
        on_render_new()
        self._content.move(direction * width, self._content.y())
        self._anim_in = tween_property(
            self._content,
            "_calendar_slide_in",
            b"pos",
            QPoint(0, self._content.y()),
            owner=self._viewport,
            duration=_DURATION_MS,
        )
        self._anim_out = tween_property(
            overlay,
            "_calendar_slide_out",
            b"pos",
            QPoint(-direction * width, overlay.y()),
            owner=self._viewport,
            duration=_DURATION_MS,
            on_finished=self._finish,
        )

    def _finish(self) -> None:
        """抢占并停止两条补间、销毁覆盖层、把内容归位。

        Note:
            作为 out 动画的 on_finished 回调，也供 run 开头清理上一次
            未结束的过渡，避免覆盖层堆叠。
        """
        stop_tween(self._viewport, "_calendar_slide_in")
        stop_tween(self._viewport, "_calendar_slide_out")
        self._anim_in = self._anim_out = None
        if self._overlay is not None:
            safe_delete(self._overlay)
            self._overlay = None
        self._content.move(0, self._content.y())

    def stop(self) -> None:
        """立即结束当前过渡并恢复稳定态。"""
        self._finish()
