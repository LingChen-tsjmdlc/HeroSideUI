"""Select and Autocomplete's shared, rotating trigger button."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPushButton

from ...animation import tween_value


class SelectorButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFlat(True)
        self.setStyleSheet("border: 0; background: transparent; padding: 0;")
        self._pixmap = None
        self._angle = 0.0
        self._angle_anim_runner = None

    def set_pixmap(self, pix):
        self._pixmap = pix
        self.update()

    def angle(self):
        return self._angle

    def set_angle(self, deg, *, animated, duration=150):
        tween_value(
            self,
            "_angle_anim_runner",
            self._angle,
            float(deg),
            self._on_angle_step,
            duration=duration,
            animated=animated,
        )

    def _on_angle_step(self, value):
        self._angle = float(value)
        self.update()

    def paintEvent(self, event):
        if self._pixmap is None or self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)
        ratio = self._pixmap.devicePixelRatio() or 1.0
        painter.drawPixmap(
            int(-self._pixmap.width() / ratio / 2),
            int(-self._pixmap.height() / ratio / 2),
            self._pixmap,
        )
        painter.end()
