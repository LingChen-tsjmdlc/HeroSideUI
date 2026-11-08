"""Table 内部容器：_GridHost（自绘 content1 实底防黑底重影）与
_CheckboxCell（整格点击热区）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from . import _palette as pal

__all__ = ["_CheckboxCell", "_GridHost"]


class _GridHost(QWidget):
    """承载网格的容器，自绘 content1 实底。

    Note:
        滚动区透明叠透明会黑底+行条重影，需先铺一层实底兜底。
    """

    def __init__(self, owner, parent=None):
        """绑定 Table 持有者并创建网格容器。

        Args:
            owner: 提供主题与 wrapper 状态的 Table 实例。
            parent: 父级 QWidget。
        """
        super().__init__(parent)
        self._owner = owner

    def paintEvent(self, e):
        """按需铺设 content1 实底以避免透明叠加导致的黑底重影。

        Args:
            e: Qt 绘制事件，本实现不读取。

        Note:
            remove_wrapper 且无滚动区时直接返回，表体直接坐在父背景上。
        """
        owner = self._owner
        # remove_wrapper 且无滚动：表体直接坐在父背景上，不铺实底（对齐 HeroUI）。
        # 其余情况（Card 内 / 滚动区内）必须铺一层 content1 实底兜底。
        if owner._remove_wrapper and owner._scroll is None:
            return
        p = QPainter(self)
        p.fillRect(self.rect(), pal.wrapper_bg(owner._theme))


class _CheckboxCell(QWidget):
    """勾选框单元格容器：整格为点击热区，两条点击路径互斥不双触发。"""

    def __init__(self, on_click, parent=None):
        """创建勾选框容器并绑定点击回调。

        Args:
            on_click: 左键点击时调用的回调。
            parent: 父级 QWidget。
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        """左键在格内释放时触发点击回调。

        Args:
            e: Qt 鼠标释放事件。
        """
        if (
            self._on_click is not None
            and e.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(e.pos())
        ):
            self._on_click()
        super().mouseReleaseEvent(e)
