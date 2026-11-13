"""输入类组件右侧的清除按钮，带淡入淡出。"""

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QPushButton, QWidget

from ...animation import tween_property


# ============================================================
# 清除按钮：带 opacity 淡入 + scale 效果
# ============================================================
class ClearButton(QPushButton):
    """点击清空文本的按钮，随内容是否为空淡入淡出。"""

    def __init__(self, parent: QWidget | None = None):
        """创建透明无边框的清除按钮。

        Args:
            parent: Qt 父对象。

        Note:
            opacity 语义：0 隐藏、0.7 正常、1.0 hover；
            初始隐藏且未启用。
        """
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; }")
        # 透明度效果：0=隐藏，0.7=正常，1.0=hover
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._opacity_anim = None

        self._visible = False

    def set_visible(self, visible: bool, animate: bool = True):
        """按 filled 状态淡入 / 淡出并同步启用态。

        Args:
            visible: True 表示显示（opacity 0.7）。
            animate: False 时直达终态，不做补间。

        Note:
            同值且 animate=True 时直接返回，避免重复启停动画。
        """
        if visible == self._visible and animate:
            return
        self._visible = visible
        tween_property(
            self._opacity_effect,
            "_opacity_anim",
            b"opacity",
            0.7 if visible else 0.0,
            owner=self,
            duration=150,
            animated=animate,
        )
        self.setEnabled(visible)

    def enterEvent(self, event):
        """鼠标进入：可见时把透明度提到 1.0。

        Args:
            event: Qt 进入事件。
        """
        if self._visible:
            tween_property(
                self._opacity_effect, "_opacity_anim", b"opacity", 1.0, owner=self, duration=150
            )
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开：可见时回落到 0.7。

        Args:
            event: Qt 离开事件。
        """
        if self._visible:
            tween_property(
                self._opacity_effect, "_opacity_anim", b"opacity", 0.7, owner=self, duration=150
            )
        super().leaveEvent(event)
