"""Dropdown 触发器 mixin：任意 widget 变菜单开关 + 焦点接管与归还。"""

import shiboken6
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QAbstractButton, QApplication


class _DropdownTriggerMixin:
    """trigger 事件绑定与焦点管理。"""

    # ============================================================
    # 绑定 / 解绑
    # ============================================================
    def _bind_trigger(self) -> None:
        """绑定 trigger：Button 走 clicked，其余走鼠标释放事件。

        Note:
            QAbstractButton 用 clicked 而不是吞事件，用户自己的 clicked
            连接不会被吃掉；同时设置手型光标并安装事件过滤器。
        """
        w = self._trigger
        if w is None:
            return
        w.installEventFilter(self)
        w.setCursor(Qt.PointingHandCursor)
        self._trigger_click_connected = False
        if isinstance(w, QAbstractButton):
            # 用 clicked 而不是吞事件，用户的 clicked 连接不会被吃掉
            w.clicked.connect(self.toggle)
            self._trigger_click_connected = True

    def _unbind_trigger(self) -> None:
        """解绑 trigger：摘过滤器、还原光标、断开 clicked。"""
        w = self._trigger
        if w is None:
            return
        w.removeEventFilter(self)
        w.setCursor(Qt.ArrowCursor)
        if self._trigger_click_connected and isinstance(w, QAbstractButton):
            try:
                w.clicked.disconnect(self.toggle)
            except (RuntimeError, TypeError):
                pass
        self._trigger_click_connected = False

    # ============================================================
    # 事件过滤
    # ============================================================
    def eventFilter(self, obj, event):
        """处理 trigger 的鼠标释放与上下键开菜单。

        Args:
            obj: 被监听对象（trigger）。
            event: 当前事件。

        Returns:
            True 表示已消费；Button 的释放事件交给 clicked 处理时返回 False。

        Note:
            上下键在未打开时直接打开菜单，禁用态忽略。
        """
        if obj is self._trigger:
            if event.type() == QEvent.MouseButtonRelease:
                # Button 已由 clicked 处理，这里只兜住非按钮 widget
                if self._trigger_click_connected:
                    return False
                if not self._is_disabled and event.button() == Qt.LeftButton:
                    self.toggle()
                    return True
            if event.type() == QEvent.KeyPress and event.key() in (
                Qt.Key_Down,
                Qt.Key_Up,
            ):
                if not self._is_disabled and not self._is_open:
                    self.open()
                return True
        return super().eventFilter(obj, event)

    # ============================================================
    # 焦点
    # ============================================================
    def _capture_focus(self) -> None:
        """记录打开前的焦点，并把焦点交给菜单首项。"""
        self._focus_before_open = QApplication.focusWidget()
        self._listbox.setFocus(Qt.OtherFocusReason)
        self._listbox.focus_first_enabled()

    def _restore_focus(self) -> None:
        """焦点仍在菜单内时才归还，避免抢走用户的新焦点。

        Note:
            记录的焦点对象可能已被销毁，用 shiboken6.isValid 校验；
            无效时退回 trigger。
        """
        fw = QApplication.focusWidget()
        if fw is None:
            return
        if fw is not self._listbox and not self._listbox.isAncestorOf(fw):
            return
        target = self._focus_before_open
        if (
            target is not None
            and shiboken6.isValid(target)
            and target.isVisible()
            and target.isEnabled()
        ):
            target.setFocus(Qt.OtherFocusReason)
        else:
            self._trigger.setFocus(Qt.OtherFocusReason)
