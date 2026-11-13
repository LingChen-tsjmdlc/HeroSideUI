"""Calendar 单月网格：只读 state 渲染，cell 复用换月不重建。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from ..._shared.dates import CalendarDate
from ._cell import _CalendarCell
from ._grid import compute_cell_state, get_weeks

_MAX_WEEKS = 6


class _MonthGrid(QWidget):
    """单个月的日期网格。cell 点击通过 date_clicked 上报（参数 CalendarDate）。"""

    date_clicked = Signal(object)
    date_hovered = Signal(object)  # 参数 CalendarDate 或 None（供范围预览）

    def __init__(
        self, state, sizes: dict, *, color: str, theme: str, col_width: int, parent=None
    ) -> None:
        """创建单月网格并预建 6×7 个复用 cell。

        Args:
            state: 实现 _GridState 协议的状态视图。
            sizes: 尺寸 token（cell_size / grid_pad_x 等）。
            color: 语义色名。
            theme: 主题名。
            col_width: 列宽，与星期名条同源。
            parent: Qt 父对象。
        """
        super().__init__(parent)
        self._state = state
        self._sizes = sizes
        self._color = color
        self._theme = theme
        self._col_width = col_width
        self._month_start: CalendarDate | None = None
        self._cells: list[list[_CalendarCell]] = []

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._build_ui()

    # ---- 构建 ---------------------------------------------------------

    def _build_ui(self) -> None:
        """构建 6 行 × 7 列的 cell 网格并接好点击与 hover 转发。"""
        pad = self._sizes["grid_pad_x"]
        cell = self._sizes["cell_size"]

        grid = QGridLayout(self)
        grid.setContentsMargins(pad, 8, pad, 8)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(self._sizes["cell_gap_y"] * 2)
        self._grid = grid

        for r in range(_MAX_WEEKS):
            row: list[_CalendarCell] = []
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
        """渲染指定月份：只换状态，不重建 cell。

        Args:
            month_start: 目标月的任意一天。
        """
        self._month_start = month_start
        self._refresh_cells()

    def _refresh_cells(self) -> None:
        """重算每个 cell 的状态并按周行数控制显隐。"""
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
        """处理 cell 点击：换算行列回日期后上报。

        Args:
            r: 行号。
            c: 列号。
        """
        cs = self._cell_state_at(r, c)
        if cs and cs.date is not None:
            self.date_clicked.emit(cs.date)

    def _cell_state_at(self, r: int, c: int):
        """取指定行列 cell 的当前状态。

        Args:
            r: 行号。
            c: 列号。

        Returns:
            对应 CellState；越界或空格时为 None。
        """
        weeks = get_weeks(self._month_start, self._state.first_day_of_week)
        if r < len(weeks):
            date = weeks[r][c]
            if date is not None:
                today = CalendarDate.today(self._month_start.identifier)
                return compute_cell_state(date, self._month_start, self._state, today)
        return None

    def eventFilter(self, obj, ev):
        """转发 cell 的 hover 事件（供范围日历预览；单选下无副作用）。

        Args:
            obj: 被监听的 cell。
            ev: 当前事件。

        Returns:
            一律交回父类。
        """
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
        """切换主题并重刷全部 cell。

        Args:
            theme: 主题名。
        """
        self._theme = theme
        if self._month_start is not None:
            self._refresh_cells()

    def set_color(self, color: str) -> None:
        """切换语义色并重刷全部 cell。

        Args:
            color: 语义色名。
        """
        self._color = color
        if self._month_start is not None:
            self._refresh_cells()
