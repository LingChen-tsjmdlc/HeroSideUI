"""_ClearButton — Input 右侧清除按钮（私有），带淡入/淡出动画。"""

from ...animation import tween_property

from PySide6.QtWidgets import QWidget
from typing import Optional

from PySide6.QtCore import (
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import QGraphicsOpacityEffect, QPushButton

from ...core import ThemeProvider
from ...utils import load_svg_icon




# ============================================================
# 清除按钮：带 opacity 淡入 + scale 效果
# ============================================================
class _ClearButton(QPushButton):
    """Clear 按钮。点击清空文本，跟随 filled 状态淡入/淡出"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 0; }"
        )
        # 透明度效果：0=隐藏，0.7=正常，1.0=hover
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._opacity_anim = None

        self._visible = False

    def set_visible(self, visible: bool, animate: bool = True):
        if visible == self._visible and animate:
            return
        self._visible = visible
        tween_property(
            self._opacity_effect, "_opacity_anim", b"opacity", 0.7 if visible else 0.0,
            owner=self, duration=150, animated=animate,
        )
        self.setEnabled(visible)

    def enterEvent(self, event):
        if self._visible:
            tween_property(self._opacity_effect, "_opacity_anim", b"opacity", 1.0,
                           owner=self, duration=150)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._visible:
            tween_property(self._opacity_effect, "_opacity_anim", b"opacity", 0.7,
                           owner=self, duration=150)
        super().leaveEvent(event)
