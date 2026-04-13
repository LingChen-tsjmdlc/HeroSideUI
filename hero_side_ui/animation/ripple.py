"""
HeroUI 风格水波纹（Ripple）动画

原理参考: https://github.com/heroui-inc/heroui/blob/main/packages/components/ripple/

实现方式:
  1. RippleOverlay 是一个透明覆盖层，叠在宿主控件上方
  2. 宿主控件在 mousePressEvent 中调用 add_ripple(pos) 记录点击坐标
  3. QPropertyAnimation 驱动 _progress 从 0→1
  4. paintEvent 中根据 progress 画扩散的半透明圆:
     - 半径 = progress × 到四角的最大距离
     - 透明度 = 0.35 × (1 - progress)
  5. 动画结束后自动清理已完成的水波纹

用法:
    overlay = RippleOverlay(parent=some_widget, color=QColor(255, 255, 255))

    # 在宿主的 mousePressEvent 中:
    overlay.add_ripple(event.position().toPoint())
"""

import re

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    Qt, QEvent, QPropertyAnimation, QEasingCurve, QPoint,
    Property, QObject, Signal,
)
from PySide6.QtGui import QPainter, QColor, QPainterPath
from typing import Optional


class _SingleRipple(QObject):
    """单个水波纹的数据和动画驱动

    每次点击创建一个实例，动画结束后由 RippleOverlay 清理
    """

    # 动画完成时发射，携带自身引用
    finished = Signal(object)

    def __init__(self, center: QPoint, max_radius: float,
                 color: QColor, duration_ms: int, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._center = center
        self._max_radius = max_radius
        self._color = QColor(color)  # 拷贝一份，避免外部修改
        self._progress = 0.0

        # 动画: progress 0 → 1
        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(duration_ms)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._anim.finished.connect(self._on_finished)

    # ---- Qt Property: progress ----
    def _get_progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float):
        self._progress = value
        # 通知父级（RippleOverlay）重绘
        if self.parent():
            self.parent().update()

    progress = Property(float, _get_progress, _set_progress)

    # ---- 公开属性 ----
    @property
    def center(self) -> QPoint:
        return self._center

    @property
    def current_radius(self) -> float:
        return self._progress * self._max_radius

    @property
    def current_color(self) -> QColor:
        """返回当前透明度的颜色 (初始 0.35 → 结束 0)"""
        c = QColor(self._color)
        alpha = int(255 * 0.35 * (1.0 - self._progress))
        c.setAlpha(max(alpha, 0))
        return c

    # ---- 控制 ----
    def start(self):
        self._anim.start()

    def _on_finished(self):
        self.finished.emit(self)


class RippleOverlay(QWidget):
    """水波纹覆盖层 — 叠在宿主控件上方，绘制所有活跃的水波纹

    参数:
        parent: 宿主控件（水波纹会跟随其大小）
        color: 水波纹颜色，默认白色半透明
        ripple_enabled: 是否启用水波纹
    """

    def __init__(self, parent: QWidget,
                 color: Optional[QColor] = None,
                 ripple_enabled: bool = True):
        super().__init__(parent)
        self._ripples: list[_SingleRipple] = []
        self._color = color or QColor(255, 255, 255)
        self._enabled = ripple_enabled

        # 覆盖层设置: 透明、不接收鼠标事件、跟随父控件大小
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(parent.rect())
        parent.installEventFilter(self)

    # ---- 公开接口 ----

    def add_ripple(self, pos: QPoint):
        """在指定位置添加一个水波纹"""
        if not self._enabled:
            return

        # 计算最大半径: 从点击点到四个角的最大距离
        w, h = self.width(), self.height()
        max_radius = max(
            _distance(pos, QPoint(0, 0)),
            _distance(pos, QPoint(w, 0)),
            _distance(pos, QPoint(0, h)),
            _distance(pos, QPoint(w, h)),
        )

        # 动画时长: 按大小缩放，clamp 在 500-900ms，保证肉眼可见的扩散过程
        duration = int(max(500, min(max_radius * 4.0, 900)))

        ripple = _SingleRipple(pos, max_radius, self._color, duration, parent=self)
        ripple.finished.connect(self._remove_ripple)
        self._ripples.append(ripple)
        ripple.start()

    def set_color(self, color: QColor):
        """更新水波纹颜色（影响后续新创建的水波纹）"""
        self._color = QColor(color)

    def set_enabled(self, enabled: bool):
        """启用/禁用水波纹"""
        self._enabled = enabled

    # ---- 内部 ----

    def _remove_ripple(self, ripple: _SingleRipple):
        """动画完成后移除"""
        if ripple in self._ripples:
            self._ripples.remove(ripple)
            ripple.deleteLater()
            self.update()

    def eventFilter(self, obj: QObject, event) -> bool:
        """跟随父控件大小变化"""
        if obj == self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
        return False

    def paintEvent(self, event):
        """绘制所有活跃的水波纹"""
        if not self._ripples:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 裁剪到父控件的圆角区域（水波纹不会溢出按钮边界）
        clip_path = QPainterPath()
        radius = self._get_parent_radius()
        clip_path.addRoundedRect(
            0.0, 0.0, float(self.width()), float(self.height()),
            radius, radius,
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
        """尝试从父控件的 QSS 中提取 border-radius"""
        parent = self.parent()
        if parent is None:
            return 0.0
        ss = parent.styleSheet()
        match = re.search(r"border-radius:\s*(\d+(?:\.\d+)?)px", ss)
        if match:
            return float(match.group(1))
        return 0.0


def _distance(p1: QPoint, p2: QPoint) -> float:
    """两点距离"""
    dx = p1.x() - p2.x()
    dy = p1.y() - p2.y()
    return (dx * dx + dy * dy) ** 0.5
