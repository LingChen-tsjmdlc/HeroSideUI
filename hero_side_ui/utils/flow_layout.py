"""FlowLayout 流式布局：hasHeightForWidth，同行子项垂直居中近似行内排版。"""

from __future__ import annotations

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget


class FlowLayout(QLayout):
    """自动折行的流式布局。

    Args:
        parent:   宿主 widget
        h_spacing: 同行相邻子项水平间距 (px)
        v_spacing: 相邻行垂直间距 (px)
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        h_spacing: int = 0,
        v_spacing: int = 4,
    ):
        """初始化布局并记录间距与子项列表。

        Args:
            parent: 宿主 widget。
            h_spacing: 同行子项水平间距（px）。
            v_spacing: 相邻行垂直间距（px）。
        """
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_space = h_spacing
        self._v_space = v_spacing
        self.setContentsMargins(QMargins(0, 0, 0, 0))

    def __del__(self):
        """逐个弹出并释放持有的布局项。"""
        while self._items:
            self._items.pop()

    # ---- QLayout 必备重写 ----
    def addItem(self, item: QLayoutItem) -> None:  # type: ignore[override]
        """追加一个布局项。"""
        self._items.append(item)

    def count(self) -> int:  # type: ignore[override]
        """返回布局项数量。"""
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # type: ignore[override]
        """返回指定索引处的布局项，越界返回 None。"""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # type: ignore[override]
        """取出并移除指定索引处的布局项，越界返回 None。"""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # type: ignore[override]
        """返回扩展方向，固定为 0。"""
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        """声明布局高度依赖宽度。"""
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        """按给定宽度试排并返回所需高度。"""
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        """应用几何区域并实际排布子项。"""
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """返回布局的建议尺寸，取最小尺寸。"""
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        """返回所有子项最小尺寸的包络并叠加内容边距。"""
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    # ---- 核心排布 ----
    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        """按行排布子项并返回所需高度，test_only 时只试排不落位。"""
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = eff.x()
        y = eff.y()
        line_height = 0
        # 逐行收集，行满时统一按行高垂直居中放置
        line_items: list[tuple] = []

        def flush_line() -> None:
            """把当前行子项按行高垂直居中落位并清空行缓冲。"""
            nonlocal line_items, line_height
            for it, ix, _iw, ih in line_items:
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
