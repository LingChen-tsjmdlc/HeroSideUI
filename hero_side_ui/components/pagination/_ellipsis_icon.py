"""Pagination DOTS 图标 (省略号 ↔ 双 chevron 切换)。

默认显示 ``heroicons--ellipsis-horizontal``;
hover/focus 时显示 ``heroicons--chevron-double-left`` (isBefore) 或
``heroicons--chevron-double-right`` (after) 暗示"快速跳转"。
"""

from typing import Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QWidget

from ...utils import load_svg_icon


class _DotsIcon(QLabel):
    """DOTS 图标载体: hover 切换 ellipsis ↔ double-chevron。"""

    def __init__(
        self, *, is_before: bool, size: int = 16, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._is_before = bool(is_before)
        self._icon_size = int(size)
        self._color: Optional[QColor] = None
        self._hover = False
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh()

    def set_icon_color(self, color: QColor):
        """主题/状态变化时刷新图标色。"""
        self._color = color
        self._refresh()

    def set_icon_size(self, size: int):
        self._icon_size = int(size)
        self.setFixedSize(self._icon_size, self._icon_size)
        self._refresh()

    def set_hover(self, hover: bool):
        """父 item 的 hover 状态由父显式驱动。"""
        h = bool(hover)
        if h == self._hover:
            return
        self._hover = h
        self._refresh()

    def _refresh(self):
        if self._hover:
            name = (
                "heroicons--chevron-double-left-solid"
                if self._is_before
                else "heroicons--chevron-double-right"
            )
        else:
            name = "heroicons--ellipsis-horizontal"
        pm = load_svg_icon(name, size=self._icon_size, color=self._color)
        self.setPixmap(pm)
        self.setFixedSize(self._icon_size, self._icon_size)


__all__ = ["_DotsIcon"]
