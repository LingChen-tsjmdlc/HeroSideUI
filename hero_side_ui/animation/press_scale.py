"""提供控件整体的按压缩放效果。"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRectF,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsEffect, QWidget


class _ScaleEffect(QGraphicsEffect):
    """居中缩放控件的源图像。"""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._scale = 1.0

    def scale(self) -> float:
        return self._scale

    def setScale(self, value: float):
        self._scale = value
        self.update()

    def draw(self, painter: QPainter):
        if self._scale >= 0.999:
            self.drawSource(painter)
            return

        pixmap = self.sourcePixmap()
        if pixmap.isNull():
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = pixmap.width()
        h = pixmap.height()
        s = self._scale

        sw = w * s
        sh = h * s
        dx = (w - sw) / 2.0
        dy = (h - sh) / 2.0

        painter.drawPixmap(QRectF(dx, dy, sw, sh), pixmap, QRectF(0, 0, w, h))
        painter.restore()


class PressScaleEffect(QObject):
    """将按下与松开状态换算为控件整体缩放。"""

    def __init__(
        self,
        target: QWidget,
        scale_factor: float = 0.97,
        press_duration: int = 80,
        release_duration: int = 150,
        parent: QObject | None = None,
    ):
        """安装并初始化按压效果。

        Args:
            target: 接受图形效果的控件。
            scale_factor: 按下后的缩放比例。
            press_duration: 按下过渡毫秒数。
            release_duration: 松开过渡毫秒数。
            parent: Qt 父对象；省略时使用 target。
        """
        super().__init__(parent or target)
        self._target = target
        self._scale_factor = scale_factor
        self._press_duration = press_duration
        self._release_duration = release_duration

        self._effect = _ScaleEffect(target)
        target.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self, b"scale_value")
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_scale(self) -> float:
        try:
            return self._effect.scale()
        except RuntimeError:
            return 1.0

    def _set_scale(self, value: float):

        try:
            self._effect.setScale(value)
        except RuntimeError:
            self._anim.stop()

    scale_value = Property(float, _get_scale, _set_scale)

    def press(self):
        """过渡到按下缩放比例。"""
        try:
            start = self._effect.scale()
        except RuntimeError:
            return
        self._anim.stop()
        self._anim.setStartValue(start)
        self._anim.setEndValue(self._scale_factor)
        self._anim.setDuration(self._press_duration)
        self._anim.start()

    def release(self):
        """恢复到原始缩放比例。"""
        try:
            start = self._effect.scale()
        except RuntimeError:
            return
        self._anim.stop()
        self._anim.setStartValue(start)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self._release_duration)
        self._anim.start()
