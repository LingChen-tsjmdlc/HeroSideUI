"""
HeroUI 风格下划线展开动画 (Underline Expand Animation)

对应 HeroUI 原版 Input 的 `underlined` 变体底部 after::伪元素效果：
    after:w-0
    group-data-[focus=true]:after:w-full
    after:origin-center
    after:transition-width

表现:
    聚焦时: 底部从中心向两侧展开一条彩色粗线（高 2px）
    失焦时: 线条从两侧收回到中心
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    Property,
    Qt,
)
from PySide6.QtGui import QPainter, QColor
from typing import Optional


class UnderlineBar(QWidget):
    """底部下划线装饰条

    从中心展开到两侧（或反向收回），宽度由 `progress` ∈ [0,1] 控制，
    高度固定为 2px，颜色可通过 set_color 设置。
    """

    def __init__(self, color: QColor | str = "#000000", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._progress = 0.0
        self._color = QColor(color) if not isinstance(color, QColor) else color
        self.setFixedHeight(2)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # Qt Property
    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def set_color(self, color: QColor | str):
        self._color = QColor(color) if not isinstance(color, QColor) else color
        self.update()

    def expand(self):
        """展开到 100%"""
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def collapse(self):
        """收回到 0"""
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def set_expanded(self, expanded: bool, animate: bool = True):
        if animate:
            if expanded:
                self.expand()
            else:
                self.collapse()
        else:
            self._anim.stop()
            self._progress = 1.0 if expanded else 0.0
            self.update()

    def paintEvent(self, event):
        if self._progress <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)

        w = self.width()
        h = self.height()
        bar_w = int(w * self._progress)
        x = (w - bar_w) // 2  # 中心对齐
        painter.drawRect(x, 0, bar_w, h)
        painter.end()
