"""流式布局 FlowLayout：子项从左到右排布，超出宽度自动换行。

用于行内混排场景（文字块与 Chip/Link 等 QWidget 同级摆放并折行）。经典
Qt FlowLayout 实现：``hasHeightForWidth`` 返回 True，高度由宽度反推。

同一行内子项按底部基线不易对齐（widget 高度不一），这里统一按行**垂直居中**，
视觉上文字与 Chip/Link 中线对齐，最贴近行内排版观感。
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget


class FlowLayout(QLayout):
    """自动折行的流式布局。

    Args:
        parent:   宿主 widget
        h_spacing: 同行相邻子项水平间距 (px)
        v_spacing: 相邻行垂直间距 (px)
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        h_spacing: int = 0,
        v_spacing: int = 4,
    ):
        super().__init__(parent)
        self._items: List[QLayoutItem] = []
        self._h_space = h_spacing
        self._v_space = v_spacing
        self.setContentsMargins(QMargins(0, 0, 0, 0))

    def __del__(self):
        while self._items:
            self._items.pop()

    # ---- QLayout 必备重写 ----
    def addItem(self, item: QLayoutItem) -> None:  # type: ignore[override]
        self._items.append(item)

    def count(self) -> int:  # type: ignore[override]
        return len(self._items)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # type: ignore[override]
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    # ---- 核心排布 ----
    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = eff.x()
        y = eff.y()
        line_height = 0
        # 逐行收集，行满时统一按行高垂直居中放置
        line_items: List[tuple] = []

        def flush_line() -> None:
            nonlocal line_items, line_height
            for it, ix, iw, ih in line_items:
                if not test_only:
                    off = (line_height - ih) // 2  # 垂直居中
                    it.setGeometry(QRect(QPoint(ix, y + off), it.sizeHint()))
            line_items = []

        for item in self._items:
            hint = item.sizeHint()
            iw, ih = hint.width(), hint.height()
            space_x = self._h_space
            next_x = x + iw + space_x
            if next_x - space_x > eff.right() + 1 and line_height > 0:
                flush_line()
                x = eff.x()
                y = y + line_height + self._v_space
                next_x = x + iw + space_x
                line_height = 0
            line_items.append((item, x, iw, ih))
            x = next_x
            line_height = max(line_height, ih)
        flush_line()
        return y + line_height - eff.y() + m.top() + m.bottom()


__all__ = ["FlowLayout"]
