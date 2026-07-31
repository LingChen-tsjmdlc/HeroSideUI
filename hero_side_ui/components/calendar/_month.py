"""Calendar 单月日期网格（只含日期格子，星期名由独立 _WeekdayBar 承载）。

只读 state 渲染，不做业务判断。列宽由外部统一传入的 col_width 决定（与星期名条
一致），日期格子固定 cell_size 在列内居中，从而与星期名对齐且 long 样式不错位。
cell 复用（同结构换月不销毁重建），行数按 weeks_in_month 动态 4~6 行。
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from ._cell import _CalendarCell
from ._date import CalendarDate
from ._grid import compute_cell_state, get_weeks

_MAX_WEEKS = 6


class _MonthGrid(QWidget):
    """单个月的日期网格。cell 点击通过 date_clicked 上报（参数 CalendarDate）。"""

    date_clicked = Signal(object)
    date_hovered = Signal(object)  # 参数 CalendarDate 或 None（供范围预览）

    def __init__(self, state, sizes: dict, *, color: str, theme: str,
                 col_width: int, parent=None) -> None:
        super().__init__(parent)
        self._state = state
        self._sizes = sizes
        self._color = color
        self._theme = theme
        self._col_width = col_width
        self._month_start: Optional[CalendarDate] = None
        self._cells: List[List[_CalendarCell]] = []

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._build_ui()

    # ---- 构建 ---------------------------------------------------------

    def _build_ui(self) -> None:
        pad = self._sizes["grid_pad_x"]
        cell = self._sizes["cell_size"]

        grid = QGridLayout(self)
        grid.setContentsMargins(pad, 8, pad, 8)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(self._sizes["cell_gap_y"] * 2)
        self._grid = grid

        for r in range(_MAX_WEEKS):
            row: List[_CalendarCell] = []
            for c in range(7):
                cb = _CalendarCell(cell, parent=self)
                cb.setFixedWidth(self._col_width)  # 列宽与星期名条一致；cell 内容居中
                cb.clicked.connect(lambda _=False, rr=r, cc=c: self._on_cell_clicked(rr, cc))
                cb.installEventFilter(self)
                grid.addWidget(cb, r, c, Qt.AlignmentFlag.AlignCenter)
                row.append(cb)
            self._cells.append(row)

    # ---- 渲染 ---------------------------------------------------------

    def render_month(self, month_start: CalendarDate) -> None:
        self._month_start = month_start
        self._refresh_cells()

    def _refresh_cells(self) -> None:
        weeks = get_weeks(self._month_start, self._state.first_day_of_week)
        today = CalendarDate.today(self._month_start.identifier)
        font = self._sizes["day_font"]
        n = len(weeks)
        for r in range(_MAX_WEEKS):
            visible = r < n
            for c in range(7):
                cb = self._cells[r][c]
                if not visible:
                    cb.hide()
                    continue
                date = weeks[r][c]
                cs = compute_cell_state(date, self._month_start, self._state, today)
                cb.apply_state(cs, color=self._color, theme=self._theme, font_size=font)
                cb.setVisible(not cs.is_empty)

    # ---- 事件 ---------------------------------------------------------

    def _on_cell_clicked(self, r: int, c: int) -> None:
        cs = self._cell_state_at(r, c)
        if cs and cs.date is not None:
            self.date_clicked.emit(cs.date)

    def _cell_state_at(self, r: int, c: int):
        weeks = get_weeks(self._month_start, self._state.first_day_of_week)
        if r < len(weeks):
            date = weeks[r][c]
            if date is not None:
                today = CalendarDate.today(self._month_start.identifier)
                return compute_cell_state(date, self._month_start, self._state, today)
        return None

    def eventFilter(self, obj, ev):
        # 转发 cell 的 hover（供范围日历预览；单选下无副作用）
        if ev.type() == QEvent.Type.Enter and isinstance(obj, _CalendarCell):
            for r, row in enumerate(self._cells):
                for c, cb in enumerate(row):
                    if cb is obj:
                        cs = self._cell_state_at(r, c)
                        self.date_hovered.emit(cs.date if cs else None)
                        break
        return super().eventFilter(obj, ev)

    # ---- 主题 / 颜色 --------------------------------------------------

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        if self._month_start is not None:
            self._refresh_cells()

    def set_color(self, color: str) -> None:
        self._color = color
        if self._month_start is not None:
            self._refresh_cells()
