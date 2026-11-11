"""_GlobalClickCatcher — Popover 全局点击监听器（私有）。

挂在 QApplication 上监听 MouseButtonPress，配合 Popover 的 ``close on outside click`` 行为。
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, QPoint
from shiboken6 import isValid

if TYPE_CHECKING:
    from .popover import Popover


# ============================================================
# 全局外部点击监听（Tool 模式下用它代替 Popup 的自动外部关闭）
# ============================================================


class _GlobalClickCatcher(QObject):
    def __init__(self, owner: "Popover"):
        """构造全局点击监听器。

        Args:
            owner: 所属的 Popover 实例，用于查询打开状态与几何。
        """
        super().__init__(owner)
        self._owner = owner

    def eventFilter(self, obj, event):
        """拦截全局鼠标按下事件，实现"点击外部关闭"。

        Args:
            obj: 事件目标对象。
            event: Qt 事件对象。

        Returns:
            bool: 始终返回 False，不拦截事件传播。

        Note:
            点到 popover 自身或 trigger 时保持打开，让 trigger 的 click
            逻辑走 toggle，避免出现"点两次才开关"的体感。
        """
        owner = self._owner
        # owner 生命周期不归本过滤器管；C++ 端已释放时只放行，
        # 继续访问其属性会在事件派发阶段变成悬空访问。
        if not isValid(owner):
            return False
        if event.type() == QEvent.Type.MouseButtonPress:
            if not owner._is_open:
                return False
            # 全局坐标
            try:
                gp = event.globalPosition().toPoint()
            except AttributeError:
                gp = event.globalPos()
            # 点到 popover 自己 → 保持打开
            if owner.geometry().contains(gp):
                return False
            # 点到 trigger → 也保持（让 trigger 的 click 逻辑走 toggle，
            # 否则这里先关一次，用户点击再开一次，体感还是"点两次")
            trigger = owner._trigger
            if trigger is not None and isValid(trigger):
                tr_top_left = trigger.mapToGlobal(QPoint(0, 0))
                w = trigger.width()
                h = trigger.height()
                if (
                    tr_top_left.x() <= gp.x() <= tr_top_left.x() + w
                    and tr_top_left.y() <= gp.y() <= tr_top_left.y() + h
                ):
                    return False
            # 外部点击 → 关
            owner.close()
        return False
