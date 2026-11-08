"""Calendar 星期名条：固定组件，翻月不动；列宽与日期网格同源。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ..text import Text
from . import _palette as pal


class _WeekdayBar(QWidget):
    def __init__(
        self, sizes: dict, *, visible_months: int, col_width: int, theme: str, parent=None
    ) -> None:
        """创建星期名条：每个可见月一段、7 个星期名格。

        Args:
            sizes: 尺寸 token（weekday_font / grid_pad_x 等）。
            visible_months: 可见月份数（多月视图时 >1）。
            col_width: 单格列宽，与日期网格同源。
            theme: 主题名。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._sizes = sizes
        self._visible_months = visible_months
        self._col_width = col_width
        self._theme = theme
        self._labels: list[Text] = []

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self._sizes["weekday_font"] + 20)
        self._build_ui()

    def _build_ui(self) -> None:
        """按可见月份数构建分段布局，每段 7 个等宽星期名格。"""
        pad = self._sizes["grid_pad_x"]
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        # 每个可见月一段：左右各留 grid_pad_x，中间 7 个 col_width 星期名格
        for _ in range(self._visible_months):
            seg = QWidget(self)
            sl = QHBoxLayout(seg)
            sl.setContentsMargins(pad, 0, pad, 0)
            sl.setSpacing(0)
            for _c in range(7):
                lbl = Text("", size="xs", color="default-400", theme=self._theme, parent=seg)
                lbl.setFixedWidth(self._col_width)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._labels.append(lbl)
                sl.addWidget(lbl)
            root.addWidget(seg)

    # ---- 绘制：content1 底 + 底部渐隐阴影 -----------------------------

    def paintEvent(self, ev) -> None:
        """绘制 content1 底色。

        Args:
            ev: Qt 绘制事件。

        Note:
            与月/年头部同为 content1 层，与日期区靠色差分层；
            不画底部阴影带——浅色主题下会显成突兀灰杠。
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        # 星期名行底与月/年头部同为 content1；与日期区靠色差分层。
        # 不画底部阴影带——浅色主题下会显成一道突兀的灰杠。
        p.fillRect(QRectF(0, 0, w, h), pal.surface_content1(self._theme))
        p.end()

    # ---- API ----------------------------------------------------------

    def set_names(self, names: list[str]) -> None:
        """填充星期名文本。

        Args:
            names: 单个月份的 7 个星期名；多月时重复填充每段。
        """
        for i, lbl in enumerate(self._labels):
            lbl.setText(names[i % 7])

    def set_theme(self, theme: str) -> None:
        """切换主题并联动星期名文字颜色。

        Args:
            theme: 主题名。
        """
        self._theme = theme
        for lbl in self._labels:
            lbl.set_theme(theme)
        self.update()
