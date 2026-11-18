"""Dialog 对父窗口的压暗 / 模糊：复用浮层家族的共享遮罩。"""

from __future__ import annotations

import shiboken6
from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtWidgets import QWidget

from ..._shared.overlays import Backdrop
from ...themes import DIALOG_BACKDROP_KINDS
from ...utils import safe_delete

# 淡出完成后再销毁遮罩，需不短于 Backdrop 的淡出时长
_FADE_OUT_MS = 220


def _below_title_bar(host: QWidget) -> QRect:
    """宿主里标题栏以下的区域；宿主不是带自绘标题栏的 Window 时为整个客户区。

    Note:
        用根布局边距与标题栏固定高度算，不读子控件几何：宿主缩放时事件过滤器先于布局执行，
        那时子控件几何还是旧值。
    """
    bar = getattr(host, "_title_bar", None)
    root = getattr(host, "_root_layout", None)
    if bar is None or root is None:
        return QRect(0, 0, host.width(), host.height())
    m = root.contentsMargins()
    top = m.top() + bar.height()
    return QRect(
        m.left(),
        top,
        max(0, host.width() - m.left() - m.right()),
        max(0, host.height() - top - m.bottom()),
    )


class _Shade:
    """持有一张盖在宿主窗口上的遮罩，打开时建、关闭时淡出并销毁。"""

    def __init__(self):
        self._backdrop: Backdrop | None = None

    def show(self, host: QWidget | None, kind: str):
        """在宿主上建遮罩并淡入。

        Args:
            host: 被遮住的窗口；None 时什么都不做。
            kind: dim 压暗 / blur 模糊；none 不建。

        Note:
            只盖标题栏以下，标题栏与窗口控制按钮保持清晰；
            遮罩要压在宿主自绘圆角的覆盖层之下，覆盖层才能擦掉圆角外的方角。
        """
        self.clear()
        if host is None or kind not in DIALOG_BACKDROP_KINDS:
            return
        bd = Backdrop(DIALOG_BACKDROP_KINDS[kind], host=host, region=lambda: _below_title_bar(host))
        bd.sync_geometry()
        if kind == "blur":
            bd.prepare_blur_snapshot()
        bd.show()
        overlay = getattr(host, "_overlay", None)
        if overlay is not None:
            bd.stackUnder(overlay)
        bd.play_in()
        self._backdrop = bd

    def fade_out(self):
        """淡出并销毁；淡出期间遮罩不再拦截宿主的鼠标事件。"""
        bd, self._backdrop = self._backdrop, None
        if bd is None or not shiboken6.isValid(bd):
            return
        bd.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        bd.play_out()
        QTimer.singleShot(_FADE_OUT_MS, bd, lambda: safe_delete(bd))

    def clear(self):
        """立即销毁，不播放淡出；遮罩已随宿主销毁时什么都不做。"""
        bd, self._backdrop = self._backdrop, None
        if bd is not None and shiboken6.isValid(bd):
            safe_delete(bd)


__all__ = ["_Shade"]
