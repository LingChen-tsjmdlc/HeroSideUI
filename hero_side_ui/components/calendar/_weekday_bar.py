"""Calendar 星期名条（固定，属于顶部亮区，翻月不动）。

对齐 HeroUI gridHeader：content1 亮底 + 底部分隔阴影。星期名由 first_day_of_week
决定、翻月永不变，故做成独立固定组件，不随日期网格滑动、不重复重绘。列宽由
外部传入的 col_width 统一（与日期网格一致），long 样式也不截断。
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ..text import Text
from . import _palette as pal


class _WeekdayBar(QWidget):
    def __init__(self, sizes: dict, *, visible_months: int, col_width: int,
                 theme: str, parent=None) -> None:
        super().__init__(parent)
        self._sizes = sizes
        self._visible_months = visible_months
        self._col_width = col_width
        self._theme = theme
        self._labels: List[Text] = []

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self._sizes["weekday_font"] + 20)
        self._build_ui()

    def _build_ui(self) -> None:
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
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        # 星期名行底与月/年头部同为 content1；与日期区靠色差分层。
        # 不画底部阴影带——浅色主题下会显成一道突兀的灰杠。
        p.fillRect(QRectF(0, 0, w, h), pal.surface_content1(self._theme))
        p.end()

    # ---- API ----------------------------------------------------------

    def set_names(self, names: List[str]) -> None:
        """names 为一个月的 7 个星期名；多月时重复填充每段。"""
        for i, lbl in enumerate(self._labels):
            lbl.setText(names[i % 7])

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        for lbl in self._labels:
            lbl.set_theme(theme)
        self.update()
