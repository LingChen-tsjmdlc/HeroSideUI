"""Table 内部容器控件。

- ``_GridHost``：承载单元格网格，自绘 content1 实心底色（滚动区透明叠透明会黑底+重影）。
- ``_CheckboxCell``：勾选框单元格容器，整格都是点击热区，消除复选框周围的点击死区。

两者都依赖宿主 Table 的 ``_theme`` / ``_remove_wrapper`` / ``_scroll`` 状态，
通过构造时传入的 owner 引用读取，不持有强业务逻辑。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from . import _palette as pal

__all__ = ["_GridHost", "_CheckboxCell"]


class _GridHost(QWidget):
    """承载单元格网格的容器，自绘 content1 实心底色。

    放进 ScrollShadow 时 viewport 是半透明的，若 grid_host 也透明则滚动区内
    没有任何不透明层 → 未清空缓冲呈黑底、半透明行条逐帧叠加成文字重影。
    这里 owner 提供当前主题底色，paintEvent 先铺一层实底兜底。
    """

    def __init__(self, owner, parent=None):
        super().__init__(parent)
        self._owner = owner

    def paintEvent(self, e):
        owner = self._owner
        # remove_wrapper 且无滚动：表体直接坐在父背景上，不铺实底（对齐 HeroUI）。
        # 其余情况（Card 内 / 滚动区内）必须铺一层 content1 实底兜底。
        if owner._remove_wrapper and owner._scroll is None:
            return
        p = QPainter(self)
        p.fillRect(self.rect(), pal.wrapper_bg(owner._theme))


class _CheckboxCell(QWidget):
    """勾选框单元格容器：整格都是点击热区，消除复选框周围的点击死区。

    点到复选框本体时，子 widget 消费事件，本类 mouseReleaseEvent 不触发；
    点到 padding / 空白时由本类转发，两条路径互斥，不会双触发。
    """

    def __init__(self, on_click, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if (
            self._on_click is not None
            and e.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(e.pos())
        ):
            self._on_click()
        super().mouseReleaseEvent(e)
