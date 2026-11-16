"""浮层命中测试：Windows 下阴影留白区域不拦截鼠标，点击穿透到下层窗口。

浮层是带透明阴影留白的顶层窗口，留白里 alpha>0 的像素会吞掉本该给下层控件的点击。
使用方实现 _body_global()，返回可见主体的全局矩形。
"""

from __future__ import annotations

import sys
from ctypes import wintypes

from PySide6.QtCore import QRect
from PySide6.QtGui import QCursor

_WM_NCHITTEST = 0x0084
_HTTRANSPARENT = -1


class HitThroughMixin:
    """留白穿透 mixin：须放在 QWidget 之前。"""

    def _body_global(self) -> QRect:
        """可见主体的全局矩形，由使用方实现。"""
        raise NotImplementedError

    def nativeEvent(self, event_type, message):
        """主体之外的命中测试返回 HTTRANSPARENT，让下层窗口接收点击。

        Args:
            event_type: 原生事件类型。
            message: 原生消息指针（Windows 下为 MSG*）。
        """
        if sys.platform == "win32" and bytes(event_type) == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == _WM_NCHITTEST and not self._body_global().contains(QCursor.pos()):
                return True, _HTTRANSPARENT
        return super().nativeEvent(event_type, message)  # type: ignore[misc]


__all__ = ["HitThroughMixin"]
