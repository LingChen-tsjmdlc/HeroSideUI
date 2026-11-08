"""行号栏：自绘右对齐行号，宽度随最大位数自适应，与编辑区同步滚动。"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from ...themes import CODE_EDITOR_LINE


class _Gutter(QWidget):
    """编辑器左侧行号栏，由 CodeEditor 驱动，本类只负责画。"""

    def __init__(self, editor: CodeEditor, parent: QWidget | None = None) -> None:  # noqa: F821
        """创建行号栏。

        Args:
            editor: 宿主 CodeEditor，用于读取块布局与滚动状态。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._editor = editor
        self._font: QFont | None = None
        self._line_height = 20
        self._current_line = 1
        self._first_visible_top = 0  # 首个可见块内容区 y 偏移
        self._visible_from = 1  # 首个可见行号
        self._visible_to = 1  # 末个可见行号
        self._theme = "light"

    def sync(
        self,
        font: QFont,
        line_height: int,
        current_line: int,
        first_block_top: int,
        visible_from: int,
        visible_to: int,
    ) -> None:
        """编辑器在光标移动 / 滚动 / 字号变化时推送状态并触发重绘。

        Args:
            font: 当前等宽字体。
            line_height: 单行高度（像素）。
            current_line: 光标所在行号。
            first_block_top: 首个可见块内容区的 y 偏移。
            visible_from: 首个可见行号。
            visible_to: 末个可见行号。
        """
        self._font = font
        self._line_height = line_height
        self._current_line = current_line
        self._first_visible_top = first_block_top
        self._visible_from = visible_from
        self._visible_to = visible_to
        self.update()

    def set_theme(self, theme: str) -> None:
        """切换行号栏主题并重绘。

        Args:
            theme: light / dark。
        """
        self._theme = theme
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """自绘可见区右对齐行号，当前行用高亮色。

        Args:
            event: Qt 绘制事件。
        """
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
                0,
                y,
                w - pad,
                self._line_height,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(n),
            )
            y += self._line_height
        painter.end()

    def sizeHint(self) -> QSize:  # type: ignore[override]
        """行号栏推荐宽度。

        Returns:
            按主题取 CODE_EDITOR_LINE 的 gutter_width，高度为 0（由宿主定）。
        """
        max(2, len(str(max(self._visible_to, 99))))
        cfg = CODE_EDITOR_LINE["dark" if self._theme == "dark" else "light"]
        return QSize(cfg["gutter_width"], 0)


__all__ = ["_Gutter"]
