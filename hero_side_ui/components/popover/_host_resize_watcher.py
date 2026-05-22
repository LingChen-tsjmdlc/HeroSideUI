"""_HostGeometryWatcher — Popover 宿主几何变化监听器（私有）。

挂在 trigger.window() 上：
- Move  → 触发"平移"重定位（与 trigger 一起整体平移即可）
- Resize → 触发"完整 _calc_position 重算"（layout 可能整体重排，trigger 相对 host 位置变了）
"""

from PySide6.QtCore import QEvent, QObject


class _HostGeometryWatcher(QObject):
    """监听 host window 的 Move / Resize，分别走平移 / 完整重算路径。"""

    def __init__(self, owner):
        super().__init__(owner)
        self._owner = owner

    def eventFilter(self, obj, event):
        if not self._owner._is_open:
            return False
        et = event.type()
        if et == QEvent.Type.Move:
            # 整窗拖动：popover 与 trigger 同步平移即可
            self._owner._on_scroll_detected(0)
        elif et == QEvent.Type.Resize:
            # 窗口缩放：layout 重排，必须完整重算位置
            self._owner._request_full_reposition()
        return False
