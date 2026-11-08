"""_ResizeGrip 右下角拖拽手柄：vertical/horizontal/both 三模式，自绘两斜线。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


# ============================================================
# Resize Grip：手动拖动改变 wrapper 高度的小手柄
# ============================================================
class _ResizeGrip(QWidget):
    """右下角小手柄，拖动改变 textarea 高度；mode 决定光标与拖动轴。"""

    drag_started = Signal()
    drag_delta = Signal(int, int)  # (dx, dy)
    drag_ended = Signal()

    def __init__(self, mode: str = "vertical", parent: QWidget | None = None):
        """初始化拖拽手柄，设置固定尺寸、光标与默认线条色。

        Args:
            mode: 拖动轴向，vertical / horizontal / both。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._mode = mode
        self._press_pos = None
        self.setFixedSize(14, 14)
        self.setCursor(self._cursor_for_mode())
        self.setMouseTracking(True)
        self._line_color = QColor("#a1a1aa")  # neutral-400 默认；外部可 set_line_color

    def _cursor_for_mode(self) -> Qt.CursorShape:
        """按拖动轴向返回对应的鼠标光标形状。"""
        if self._mode == "horizontal":
            return Qt.CursorShape.SizeHorCursor
        if self._mode == "both":
            return Qt.CursorShape.SizeFDiagCursor
        return Qt.CursorShape.SizeVerCursor  # vertical 默认

    def set_mode(self, mode: str):
        """设置拖动轴向并刷新光标。"""
        self._mode = mode
        self.setCursor(self._cursor_for_mode())
        self.update()

    def set_line_color(self, color: QColor):
        """设置斜线颜色并触发重绘。"""
        self._line_color = QColor(color)
        self.update()

    # ---- 鼠标事件：分发 drag_started / drag_delta / drag_ended ----
    def mousePressEvent(self, event):
        """左键按下时记录起点并发出 drag_started。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self.drag_started.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        """按住拖动时按轴向锁定并发出 drag_delta。"""
        if self._press_pos is not None:
            cur = event.globalPosition().toPoint()
            dx = cur.x() - self._press_pos.x()
            dy = cur.y() - self._press_pos.y()
            # 锁轴
            if self._mode == "vertical":
                dx = 0
            elif self._mode == "horizontal":
                dy = 0
            self.drag_delta.emit(dx, dy)
            self._press_pos = cur
            event.accept()

    def mouseReleaseEvent(self, event):
        """左键松开时清除起点并发出 drag_ended。"""
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            self._press_pos = None
            self.drag_ended.emit()
            event.accept()

    # ---- 自绘两条斜线 ----
    def paintEvent(self, event):
        """在右下角自绘两条 45° 斜线。"""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._line_color)
        pen.setWidth(1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        w = self.width()
        h = self.height()
        # 两条 45° 斜线（HTML textarea 风格）：从右下角向左上扩散
        # 短线
        p.drawLine(w - 3, h - 8, w - 8, h - 3)
        # 长线
        p.drawLine(w - 3, h - 4, w - 4, h - 3)
