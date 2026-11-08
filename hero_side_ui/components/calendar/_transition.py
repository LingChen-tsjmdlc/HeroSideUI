"""Calendar 翻页滑动过渡（对齐 HeroUI framer slideVariants）。

翻页时：把旧网格 grab 成 pixmap 叠一层，新网格立即渲染在底层，然后旧层向
direction 反向滑出、新层从 direction 方向滑入，结束销毁旧层。纯 setPixmap 的
QLabel 覆盖层无交互子控件、不加 QGraphicsEffect，规避离屏渲染错位。
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPropertyAnimation
from PySide6.QtWidgets import QLabel, QWidget

from ...animation import stop_tween, tween_property
from ...utils import safe_delete

_DURATION_MS = 250


class _SlideTransition:
    """管理单个网格容器的翻页滑动。宿主需提供一个固定尺寸的 viewport widget。"""

    def __init__(self, viewport: QWidget, content: QWidget) -> None:
        self._viewport = viewport
        self._content = content
        self._overlay: QLabel | None = None
        self._anim_in: QPropertyAnimation | None = None
        self._anim_out: QPropertyAnimation | None = None

    def is_active(self) -> bool:
        return self._overlay is not None

    def run(self, direction: int, on_render_new) -> None:
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
        stop_tween(self._viewport, "_calendar_slide_in")
        stop_tween(self._viewport, "_calendar_slide_out")
        self._anim_in = self._anim_out = None
        if self._overlay is not None:
            safe_delete(self._overlay)
            self._overlay = None
        self._content.move(0, self._content.y())

    def stop(self) -> None:
        self._finish()
