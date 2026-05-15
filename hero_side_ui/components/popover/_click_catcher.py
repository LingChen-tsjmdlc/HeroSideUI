"""_GlobalClickCatcher — Popover 全局点击监听器（私有）。

挂在 QApplication 上监听 MouseButtonPress，配合 Popover 的 ``close on outside click`` 行为。
"""

from PySide6.QtCore import QPoint

from PySide6.QtCore import QEvent, QObject, Signal




# ============================================================
# 全局外部点击监听（Tool 模式下用它代替 Popup 的自动外部关闭）
# ============================================================


class _GlobalClickCatcher(QObject):
    def __init__(self, owner: "Popover"):
        super().__init__(owner)
        self._owner = owner

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if not self._owner._is_open:
                return False
            # 全局坐标
            try:
                gp = event.globalPosition().toPoint()
            except AttributeError:
                gp = event.globalPos()
            # 点到 popover 自己 → 保持打开
            if self._owner.geometry().contains(gp):
                return False
            # 点到 trigger → 也保持（让 trigger 的 click 逻辑走 toggle，
            # 否则这里先关一次，用户点击再开一次，体感还是"点两次")
            if self._owner._trigger is not None:
                tr_top_left = self._owner._trigger.mapToGlobal(QPoint(0, 0))
                w = self._owner._trigger.width()
                h = self._owner._trigger.height()
                if (
                    tr_top_left.x() <= gp.x() <= tr_top_left.x() + w
                    and tr_top_left.y() <= gp.y() <= tr_top_left.y() + h
                ):
                    return False
            # 外部点击 → 关
            self._owner.close()
        return False
