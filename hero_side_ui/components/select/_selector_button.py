"""_SelectorButton — Select 右侧的下拉箭头按钮（私有）。

复刻自 Autocomplete 的同名子组件：自绘 svg + QTransform 旋转动画。
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QPushButton

from ...animation import tween_value


class _SelectorButton(QPushButton):
    """selector 按钮：底层 svg + 通过 QTransform 旋转。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFlat(True)
        self.setStyleSheet("border: 0; background: transparent; padding: 0;")
        self._pixmap: Optional[QPixmap] = None
        self._angle: float = 0.0
        self._angle_anim_runner = None

    def set_pixmap(self, pix: QPixmap):
        self._pixmap = pix
        self.update()

    def angle(self) -> float:
        return self._angle

    def set_angle(self, deg: float, *, animated: bool, duration: int = 150):
        if animated and self._angle != deg:
            tween_value(
                self,
                "_angle_anim_runner",
                float(self._angle),
                float(deg),
                self._on_angle_step,
                duration=duration,
            )
        else:
            self._angle = deg
            self.update()

    def _on_angle_step(self, v):
        self._angle = float(v)
        self.update()

    def paintEvent(self, e):
        if self._pixmap is None or self._pixmap.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.Antialiasing, True)
        cx = self.width() / 2
        cy = self.height() / 2
        p.translate(cx, cy)
        p.rotate(self._angle)
        dpr = self._pixmap.devicePixelRatio() or 1.0
        dw = self._pixmap.width() / dpr
        dh = self._pixmap.height() / dpr
        p.drawPixmap(int(-dw / 2), int(-dh / 2), self._pixmap)
        p.end()
