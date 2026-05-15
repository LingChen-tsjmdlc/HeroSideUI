"""Accordion 组件的展开/收起箭头 — 私有子组件。"""

from PySide6.QtCore import Property
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from ...utils import load_svg_icon


class _IndicatorWidget(QWidget):
    """展开/收起箭头指示器 — 使用 SVG 图标渲染

    默认显示向右的 chevron，展开时顺时针旋转 90° 变成向下。
    """

    def __init__(self, icon_name: str = "heroicons--chevron-right-solid", parent=None):
        super().__init__(parent)
        self._rotation = 0.0
        self._color = QColor("#a1a1aa")
        self._icon_name = icon_name
        self._pixmap = None
        self._update_pixmap()

    # Qt Property: rotation（供 QPropertyAnimation 驱动）
    def _get_rotation(self) -> float:
        return self._rotation

    def _set_rotation(self, value: float):
        self._rotation = value
        self.update()

    def set_rotation(self, value: float):
        self._rotation = value
        self.update()

    rotation = Property(float, _get_rotation, _set_rotation)

    def set_color(self, color: QColor):
        self._color = color
        self._update_pixmap()
        self.update()

    def set_icon(self, icon_name: str):
        """替换图标"""
        self._icon_name = icon_name
        self._update_pixmap()
        self.update()

    def _update_pixmap(self):
        """重新渲染 SVG 图标"""
        from ...utils import load_svg_icon
        size = max(self.width(), self.height(), 18)
        self._pixmap = load_svg_icon(self._icon_name, size=size, color=self._color)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def paintEvent(self, event):
        if self._pixmap is None or self._pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        # 居中旋转
        painter.translate(cx, cy)
        painter.rotate(self._rotation)
        painter.translate(-cx, -cy)

        # 居中绘制 pixmap
        px = (w - self._pixmap.width()) / 2.0
        py = (h - self._pixmap.height()) / 2.0
        painter.drawPixmap(int(px), int(py), self._pixmap)

        painter.end()
