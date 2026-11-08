"""提供按点击位置扩散的水波纹和透明覆盖层。"""

import re

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget


class _SingleRipple(QObject):
    """维护一个水波纹的扩散和透明度。

    Attributes:
        finished: 完成时携带自身对象的信号。
    """

    finished = Signal(object)

    def __init__(
        self,
        center: QPoint,
        max_radius: float,
        color: QColor,
        duration_ms: int,
        parent: QObject | None = None,
    ):
        """初始化单个水波纹。

        Args:
            center: 覆盖层坐标中的圆心。
            max_radius: 终态半径，单位为像素。
            color: 水波纹基色。
            duration_ms: 扩散毫秒数。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._center = center
        self._max_radius = max_radius
        self._color = QColor(color)
        self._progress = 0.0

        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(duration_ms)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.finished.connect(self._on_finished)

    def _get_progress(self) -> float:
        """返回当前扩散进度。"""
        return self._progress

    def _set_progress(self, value: float):
        """设置扩散进度并请求父级重绘。"""
        self._progress = value

        if self.parent():
            self.parent().update()

    progress = Property(float, _get_progress, _set_progress)

    @property
    def center(self) -> QPoint:
        """返回水波纹圆心。"""
        return self._center

    @property
    def current_radius(self) -> float:
        """返回当前扩散半径。"""
        return self._progress * self._max_radius

    @property
    def current_color(self) -> QColor:
        """返回随扩散进度逐渐透明的颜色。"""
        c = QColor(self._color)
        alpha = int(255 * 0.35 * (1.0 - self._progress))
        c.setAlpha(max(alpha, 0))
        return c

    def start(self):
        """启动扩散动画。"""
        self._anim.start()

    def _on_finished(self):
        """发出携带自身的完成信号。"""
        self.finished.emit(self)


class RippleOverlay(QWidget):
    """在宿主上叠加可独立退场的水波纹。"""

    def __init__(self, parent: QWidget, color: QColor | None = None, ripple_enabled: bool = True):
        """初始化不拦截鼠标的透明覆盖层。

        Args:
            parent: 需要覆盖的宿主控件。
            color: 水波纹基色；省略时使用白色。
            ripple_enabled: 是否接受新的水波纹请求。
        """
        super().__init__(parent)
        self._ripples: list[_SingleRipple] = []
        self._color = color or QColor(255, 255, 255)
        self._enabled = ripple_enabled

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(parent.rect())
        parent.installEventFilter(self)

    def add_ripple(self, pos: QPoint):
        """在启用状态下添加并播放水波纹。

        Args:
            pos: 相对覆盖层的点击位置。
        """
        if not self._enabled:
            return

        w, h = self.width(), self.height()
        max_radius = max(
            _distance(pos, QPoint(0, 0)),
            _distance(pos, QPoint(w, 0)),
            _distance(pos, QPoint(0, h)),
            _distance(pos, QPoint(w, h)),
        )

        duration = int(max(500, min(max_radius * 4.0, 900)))

        ripple = _SingleRipple(pos, max_radius, self._color, duration, parent=self)
        ripple.finished.connect(self._remove_ripple)
        self._ripples.append(ripple)
        ripple.start()

    def set_color(self, color: QColor):
        """设置后续新水波纹的基色。

        Args:
            color: 新的基色。
        """
        self._color = QColor(color)

    def set_enabled(self, enabled: bool):
        """控制是否接受新水波纹，不取消已在播放的波纹。

        Args:
            enabled: 是否启用。
        """
        self._enabled = enabled

    def _remove_ripple(self, ripple: _SingleRipple):
        """移除已完成的水波纹并安排延迟删除。"""
        if ripple in self._ripples:
            self._ripples.remove(ripple)
            ripple.deleteLater()
            self.update()

    def eventFilter(self, obj: QObject, event) -> bool:
        """随宿主尺寸变化更新覆盖区域。"""
        if obj == self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
        return False

    def paintEvent(self, event):
        """在宿主圆角范围内绘制当前水波纹。"""
        if not self._ripples:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        clip_path = QPainterPath()
        radius = self._get_parent_radius()
        clip_path.addRoundedRect(
            0.0,
            0.0,
            float(self.width()),
            float(self.height()),
            radius,
            radius,
        )
        painter.setClipPath(clip_path)

        for ripple in self._ripples:
            color = ripple.current_color
            r = ripple.current_radius
            center = ripple.center

            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, int(r), int(r))

        painter.end()

    def _get_parent_radius(self) -> float:
        """读取宿主 QSS 中的像素圆角，未指定时返回 0。"""
        parent = self.parent()
        if parent is None:
            return 0.0
        ss = parent.styleSheet()
        match = re.search(r"border-radius:\s*(\d+(?:\.\d+)?)px", ss)
        if match:
            return float(match.group(1))
        return 0.0


def _distance(p1: QPoint, p2: QPoint) -> float:
    """两点距离。"""
    dx = p1.x() - p2.x()
    dy = p1.y() - p2.y()
    return (dx * dx + dy * dy) ** 0.5
