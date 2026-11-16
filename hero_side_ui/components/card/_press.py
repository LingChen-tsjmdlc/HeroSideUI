"""Card 按压透传：内容子树里的文字等控件收到鼠标按压时，卡片也响应。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QTimer, Qt
from PySide6.QtWidgets import QWidget


class CardPressMixin:
    """把内容子树的鼠标按压转发给卡片，同时保留子控件自己的事件处理。

    依赖宿主提供 _content / _is_pressable / _is_disabled / _is_pressed_state /
    _press_scale / _ripple_overlay / pressed。
    """

    def install_press_forwarding(self, content: QWidget) -> None:
        """给内容根节点及其当前子控件装上事件过滤器。

        Args:
            content: 卡片的内容根控件。
        """
        self._handled_mouse = None
        content.installEventFilter(self)
        for child in content.findChildren(QWidget):
            child.installEventFilter(self)

    def _press_at(self, pos: QPoint) -> None:
        """在卡片坐标 pos 处开始按压动画。

        Args:
            pos: 卡片外壳坐标系内的按下位置。
        """
        if self._is_pressable and not self._is_disabled:
            self._is_pressed_state = True
            if self._ripple_overlay:
                # 水波纹覆盖层挂在内层 _content 上
                self._ripple_overlay.add_ripple(self._content.mapFrom(self, pos))
            if self._press_scale:
                self._press_scale.press()

    def _release_at(self, pos: QPoint) -> None:
        """结束按压；仍在卡片内才发 pressed 信号。

        Args:
            pos: 卡片外壳坐标系内的抬起位置。
        """
        if self._press_scale:
            self._press_scale.release()
        if self._is_pressed_state:
            self._is_pressed_state = False
            if self.rect().contains(pos):
                self.pressed.emit()

    @staticmethod
    def _mouse_key(event) -> tuple:
        """同一鼠标事件的身份（id 会在按下/抬起间复用，须连同类型一起）。"""
        return (id(event), int(event.type()))

    def _clear_mouse_key(self) -> None:
        """事件分派结束后清除标记。"""
        self._handled_mouse = None

    def mousePressEvent(self, event):
        """鼠标按下：pressable 时触发水波纹与按压缩放。

        Args:
            event: Qt 鼠标按下事件。
        """
        key = self._mouse_key(event)
        if self._handled_mouse != key and event.button() == Qt.MouseButton.LeftButton:
            self._press_at(event.position().toPoint())
        self._handled_mouse = None
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放：恢复缩放，仍在卡内才发 pressed 信号。

        Args:
            event: Qt 鼠标释放事件。
        """
        key = self._mouse_key(event)
        if self._handled_mouse != key and event.button() == Qt.MouseButton.LeftButton:
            self._release_at(event.position().toPoint())
        self._handled_mouse = None
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, event):
        """把内容子树里的鼠标按压透传给卡片（文字等子控件仍可正常处理自己的事件）。

        Args:
            obj: 被过滤的对象。
            event: Qt 事件。

        Note:
            新装进来的子控件通过 ChildAdded 事件自动挂上过滤器：
            这样 add_header / add_body / add_footer 之后放入的文字也能触发卡片按压。
            同一个事件会沿子控件到父控件传播多次，用 _handled_mouse 去重；
            标记在本次事件分派结束后由定时器清除。
        """
        if event.type() == QEvent.Type.ChildAdded:
            child = event.child()
            if isinstance(child, QWidget):
                child.installEventFilter(self)
                for descendant in child.findChildren(QWidget):
                    descendant.installEventFilter(self)
        elif isinstance(obj, QWidget) and obj is not self:
            et = event.type()
            if et in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
                key = self._mouse_key(event)
                if self._handled_mouse != key and event.button() == Qt.MouseButton.LeftButton:
                    self._handled_mouse = key
                    QTimer.singleShot(0, self, self._clear_mouse_key)
                    pos = obj.mapTo(self, event.position().toPoint())
                    if et == QEvent.Type.MouseButtonPress:
                        self._press_at(pos)
                    else:
                        self._release_at(pos)
        return False
