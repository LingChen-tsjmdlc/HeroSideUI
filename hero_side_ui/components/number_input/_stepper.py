"""_NumberStepper — NumberInput 右侧垂直步进按钮组（私有）。

对齐官方 NumberInputStepper：两个透明小按钮垂直排列（上=增、下=减），
hover 降透明度到 0.7、按下 0.5；图标随语义色着色。单击单步，
不做按住连发（官方原生按钮同样无连发）。
"""

from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...utils import load_svg_icon

# 资源库中成对的上下箭头（heroicons 无 chevron-up，故选 teenyicons 成对）
UP_ICON = "teenyicons--up-solid"
DOWN_ICON = "teenyicons--down-solid"


class _StepperButton(QPushButton):
    """单个步进按钮：透明背景 + opacity hover/pressed 反馈。"""

    def __init__(self, icon_name: str, icon_size: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._icon_size = icon_size
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 0; }"
        )
        self.setFixedSize(icon_size + 8, icon_size + 8)
        self.setIconSize(QSize(icon_size, icon_size))

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

    def set_icon_color(self, color: QColor):
        """重新渲染 SVG 图标（语义色 / 主题变化时调用）。"""
        self.setIcon(load_svg_icon(self._icon_name, size=self._icon_size, color=color))

    def enterEvent(self, event):  # noqa: N802
        if self.isEnabled():
            self._opacity_effect.setOpacity(0.7)
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._opacity_effect.setOpacity(1.0)
        super().leaveEvent(event)

    def mousePressEvent(self, event):  # noqa: N802
        if self.isEnabled():
            self._opacity_effect.setOpacity(0.5)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._opacity_effect.setOpacity(0.7 if self.underMouse() else 1.0)
        super().mouseReleaseEvent(event)


class _NumberStepper(QWidget):
    """垂直步进按钮组：上=增(+1)、下=减(-1)，发 stepped(+1/-1)。

    :param button_size: 每个按钮的边长（图标取 button_size-6）
    """

    stepped = Signal(int)

    def __init__(self, button_size: int = 18, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._button_size = button_size

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        icon_size = max(8, button_size - 6)
        self._up_btn = _StepperButton(UP_ICON, icon_size)
        self._down_btn = _StepperButton(DOWN_ICON, icon_size)
        self._up_btn.clicked.connect(lambda: self.stepped.emit(1))
        self._down_btn.clicked.connect(lambda: self.stepped.emit(-1))
        layout.addWidget(self._up_btn, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._down_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def set_icon_color(self, color: QColor):
        """同步两个按钮的图标颜色。"""
        self._up_btn.set_icon_color(color)
        self._down_btn.set_icon_color(color)

    def set_buttons_enabled(self, enabled: bool):
        """disabled/readonly 时禁用按钮（Qt 禁用会自带变灰）。"""
        self._up_btn.setEnabled(enabled)
        self._down_btn.setEnabled(enabled)
        if not enabled:
            self._up_btn._opacity_effect.setOpacity(1.0)
            self._down_btn._opacity_effect.setOpacity(1.0)

    def set_button_size(self, button_size: int):
        """outside 系 label placement 下按钮整体缩小。"""
        if button_size == self._button_size:
            return
        self._button_size = button_size
        icon_size = max(8, button_size - 6)
        for btn in (self._up_btn, self._down_btn):
            btn._icon_size = icon_size
            btn.setFixedSize(icon_size + 8, icon_size + 8)
            btn.setIconSize(QSize(icon_size, icon_size))
