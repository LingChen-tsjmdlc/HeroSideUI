"""_TabList — Tabs 主组件内部存放 TabItem 的水平/垂直容器（私有）。

负责自绘容器底色 + 圆角（variant 决定外观）；不直接管理 item 切换逻辑。
"""

from PySide6.QtCore import QRectF

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from ...themes import HEROUI_COLORS, RADIUS
from ._helpers import _resolve_list_bg, _resolve_list_border




# ============================================================
# TabList: 容器（自绘背景 + 边框 + 圆角）
# ============================================================


class _TabList(QFrame):
    """tabList 容器，内部布局放 cursor + tabs。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._variant = "solid"
        self._theme = "light"
        self._radius_px = 8
        self._border_width = 0
        self._bg = None
        self._border = None
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def configure(self, *, variant=None, theme=None, radius_px=None, border_width=None):
        if variant is not None: self._variant = variant
        if theme is not None: self._theme = theme
        if radius_px is not None: self._radius_px = radius_px
        if border_width is not None: self._border_width = border_width
        self._bg = _resolve_list_bg(self._variant, self._theme)
        self._border = _resolve_list_border(self._variant, self._theme)
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        if self._radius_px > 0:
            path.addRoundedRect(rect, self._radius_px, self._radius_px)
        else:
            path.addRect(rect)

        if self._bg is not None:
            p.fillPath(path, self._bg)

        if self._border is not None and self._border_width > 0:
            pen = QPen(self._border)
            pen.setWidth(self._border_width)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)

            # bordered 还有 shadow-xs；这里简化为不画
        p.end()
