"""Calendar 翻页滑动过渡（对齐 HeroUI framer slideVariants）。

翻页时：把旧网格 grab 成 pixmap 叠一层，新网格立即渲染在底层，然后旧层向
direction 反向滑出、新层从 direction 方向滑入，结束销毁旧层。纯 setPixmap 的
QLabel 覆盖层无交互子控件、不加 QGraphicsEffect，规避离屏渲染错位。
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QPoint, Qt
from PySide6.QtWidgets import QLabel, QWidget

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
        """direction: +1 下一页（新内容从右侧进），-1 上一页（从左侧进）。

        on_render_new: 回调，在旧内容已被快照后调用，用于把 content 刷新成新月。
        """
        w = self._viewport.width()
        h = self._viewport.height()
        if w <= 0 or h <= 0:
            on_render_new()
            return

        self._finish()  # 若上一次动画未结束，先收尾

        # 1) 快照旧内容
        old_pix = self._content.grab()
        overlay = QLabel(self._viewport)
        overlay.setPixmap(old_pix)
        overlay.setGeometry(self._content.geometry())
        overlay.show()
        overlay.raise_()
        self._overlay = overlay

        # 2) 渲染新内容到底层 content
        on_render_new()

        # 3) 新内容起始位置在 direction 方向偏移一屏
        start_x = direction * w
        self._content.move(start_x, self._content.y())

        # 4) 旧层滑出到反方向，新层滑入到 0
        self._anim_out = self._make_anim(overlay, QPoint(-direction * w, overlay.y()))
        self._anim_in = self._make_anim(self._content, QPoint(0, self._content.y()))
        self._anim_out.finished.connect(self._finish)
        self._anim_out.start()
        self._anim_in.start()

    def _make_anim(self, target: QWidget, end: QPoint) -> QPropertyAnimation:
        anim = QPropertyAnimation(target, b"pos", self._viewport)
        anim.setDuration(_DURATION_MS)
        anim.setStartValue(target.pos())
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        return anim

    def _finish(self) -> None:
        if self._anim_in is not None:
            self._anim_in.stop()
            self._anim_in = None
        if self._anim_out is not None:
            self._anim_out.stop()
            self._anim_out = None
        if self._overlay is not None:
            safe_delete(self._overlay)
            self._overlay = None
        # 确保新内容归位
        self._content.move(0, self._content.y())

    def stop(self) -> None:
        self._finish()
