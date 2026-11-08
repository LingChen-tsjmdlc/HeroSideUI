"""Select and Autocomplete's shared, rotating trigger button."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QPushButton

from ...animation import tween_value


class SelectorButton(QPushButton):
    """供 Select 与 Autocomplete 共用的可旋转触发按钮。"""

    def __init__(self, parent=None):
        """初始化按钮，配置外观并重置旋转状态。

        Args:
            parent: 父控件。
        """
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFlat(True)
        self.setStyleSheet("border: 0; background: transparent; padding: 0;")
        self._pixmap = None
        self._angle = 0.0
        self._angle_anim_runner = None

    def set_pixmap(self, pix):
        """设置按钮图标并触发重绘。

        Args:
            pix: 要绘制的图标位图。
        """
        self._pixmap = pix
        self.update()

    def angle(self):
        """返回当前旋转角度。"""
        return self._angle

    def set_angle(self, deg, *, animated, duration=150):
        """将按钮旋转到目标角度。

        Args:
            deg: 目标角度。
            animated: 是否播放过渡动画。
            duration: 过渡时长，单位为毫秒。
        """
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
        """每帧更新旋转角度并触发重绘。

        Args:
            value: 当前帧的插值角度。
        """
        self._angle = float(value)
        self.update()

    def paintEvent(self, event):
        """以中心为原点旋转并绘制图标，图标为空时跳过。

        Args:
            event: Qt 绘制事件。
        """
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
