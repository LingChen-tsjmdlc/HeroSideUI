"""宿主几何监听：Move 平移跟随，Resize 触发完整重定位。"""

from PySide6.QtCore import QEvent, QObject


class _HostGeometryWatcher(QObject):
    """监听 host window 的 Move / Resize，分别走平移 / 完整重算路径。"""

    def __init__(self, owner):
        """构造宿主几何监听器。

        Args:
            owner: 所属的 Popover 实例，用于查询打开状态与触发重定位。
        """
        super().__init__(owner)
        self._owner = owner

    def eventFilter(self, obj, event):
        """拦截宿主窗口的 Move / Resize 事件。

        Args:
            obj: 事件目标对象。
            event: Qt 事件对象。

        Returns:
            bool: 始终返回 False，不拦截事件传播。

        Note:
            整窗 Move 走平移跟随；Resize（layout 重排）走完整重定位。
        """
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
