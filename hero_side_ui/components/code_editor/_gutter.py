"""行号栏（gutter）：QWidget 自绘，与编辑区同字体/同行距/同步滚动。

画法：每行一个行号，右对齐；当前行用正文色、其余用弱化色。宽度随
最大行号位数自适应（如 1→9 占一位，10→99 占两位）。
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from ...themes import CODE_EDITOR_LINE


class _Gutter(QWidget):
    """编辑器左侧行号栏。

    由 CodeEditor 持有并驱动：字体/行高/当前行/首个可见块由编辑器同步，
    本类只负责画。不要单独使用。
    """

    def __init__(self, editor: "CodeEditor", parent: QWidget | None = None) -> None:  # noqa: F821
        super().__init__(parent)
        self._editor = editor
        self._font: QFont | None = None
        self._line_height = 20
        self._current_line = 1
        self._first_visible_top = 0          # 首个可见块内容区 y 偏移
        self._visible_from = 1               # 首个可见行号
        self._visible_to = 1                 # 末个可见行号
        self._theme = "light"

    def sync(self, font: QFont, line_height: int, current_line: int,
             first_block_top: int, visible_from: int, visible_to: int) -> None:
        """编辑器在光标移动/滚动/字号变化时推送状态并触发重绘。"""
        self._font = font
        self._line_height = line_height
        self._current_line = current_line
        self._first_visible_top = first_block_top
        self._visible_from = visible_from
        self._visible_to = visible_to
        self.update()

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        line_cfg = CODE_EDITOR_LINE["dark" if self._theme == "dark" else "light"]

        if self._font is not None:
            painter.setFont(self._font)
        pad = line_cfg["gutter_pad_x"]
        text_normal = QColor(line_cfg["gutter_text"])
        text_current = QColor(line_cfg["gutter_current"])

        painter.setPen(text_normal)
        w = self.width()
        y = self._first_visible_top
        for n in range(self._visible_from, self._visible_to + 1):
            painter.setPen(text_current if n == self._current_line else text_normal)
            painter.drawText(
                0, y, w - pad, self._line_height,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(n),
            )
            y += self._line_height
        painter.end()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        digits = max(2, len(str(max(self._visible_to, 99))))
        cfg = CODE_EDITOR_LINE["dark" if self._theme == "dark" else "light"]
        return QSize(cfg["gutter_width"], 0)


__all__ = ["_Gutter"]
