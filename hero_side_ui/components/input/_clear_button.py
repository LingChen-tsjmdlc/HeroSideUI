"""_ClearButton — Input 右侧清除按钮（私有），带淡入/淡出动画。"""

from PySide6.QtWidgets import QWidget
from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
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

        self._opacity_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._opacity_anim.setDuration(150)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._visible = False

    def set_visible(self, visible: bool, animate: bool = True):
        """显示/隐藏（带淡入淡出）"""
        if visible == self._visible:
            return
        self._visible = visible
        target = 0.7 if visible else 0.0
        if animate:
            self._opacity_anim.stop()
            self._opacity_anim.setStartValue(self._opacity_effect.opacity())
            self._opacity_anim.setEndValue(target)
            self._opacity_anim.start()
        else:
            self._opacity_effect.setOpacity(target)

        # 禁用时不响应点击
        self.setEnabled(visible)

    def enterEvent(self, event):
        if self._visible:
            self._opacity_anim.stop()
            self._opacity_anim.setStartValue(self._opacity_effect.opacity())
            self._opacity_anim.setEndValue(1.0)
            self._opacity_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._visible:
            self._opacity_anim.stop()
            self._opacity_anim.setStartValue(self._opacity_effect.opacity())
            self._opacity_anim.setEndValue(0.7)
            self._opacity_anim.start()
        super().leaveEvent(event)
