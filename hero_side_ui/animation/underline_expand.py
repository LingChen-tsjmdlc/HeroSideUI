"""提供从中心展开的输入下划线。"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class UnderlineBar(QWidget):
    """绘制并控制下划线的展开进度。"""

    def __init__(self, color: QColor | str = "#000000", parent: QWidget | None = None):
        """初始化下划线控件。

        Args:
            color: 下划线颜色。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._progress = 0.0
        self._color = QColor(color) if not isinstance(color, QColor) else color
        self.setFixedHeight(2)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_progress(self) -> float:
        """返回当前展开进度。"""
        return self._progress

    def _set_progress(self, value: float):
        """设置展开进度并请求重绘。"""
        self._progress = max(0.0, min(1.0, value))
        self.update()

    progress = Property(float, _get_progress, _set_progress)

    def set_color(self, color: QColor | str):
        """更新下划线颜色并重绘。

        Args:
            color: 新的颜色。
        """
        self._color = QColor(color) if not isinstance(color, QColor) else color
        self.update()

    def expand(self):
        """展开到完整宽度。"""
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def collapse(self):
        """收回到零宽度。"""
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def set_expanded(self, expanded: bool, animate: bool = True):
        """设置下划线目标状态。

        Args:
            expanded: 是否展开。
            animate: 是否播放过渡。
        """
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
        """从中心绘制当前进度对应的下划线。"""
        if self._progress <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)

        w = self.width()
        h = self.height()
        bar_w = int(w * self._progress)
        x = (w - bar_w) // 2
        painter.drawRect(x, 0, bar_w, h)
        painter.end()
