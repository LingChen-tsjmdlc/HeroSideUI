"""RangeCalendar 范围日历（对外组件）。

复用 Calendar 的全部渲染骨架，仅替换状态机为 RangeCalendarState 并接入
范围选择行为：两次点击锚定起止、hover 实时预览、起止端点圆角 + 中间连接背景
（视觉由 _cell 根据 CellState 的 range_* 状态位绘制）。

change 信号发射 (start, end) 元组（均为 CalendarDate）。
"""

from __future__ import annotations

from typing import Optional, Tuple

from .calendar import Calendar
from ._date import CalendarDate
from ._range_state import RangeCalendarState
from ._state import CalendarState


class RangeCalendar(Calendar):
    def _create_state(self, *, value=None, **kwargs) -> CalendarState:
        # value 对范围日历是 (start, end) 元组
        state = RangeCalendarState(value=value, **kwargs)
        state.on_range_change = self._on_range_change
        return state

    def _on_range_change(self, rng) -> None:
        self._render_all()
        self.change.emit(rng)

    # ---- 覆盖交互：范围点击 + hover 预览 ------------------------------

    def _on_date_clicked(self, date: CalendarDate) -> None:
        self._state.select_date(date)
        # 选择进行中（已锚定第一端点）时，实时刷新网格显示预览
        self._render_months()

    def _on_date_hovered(self, date) -> None:
        # 仅在已锚定第一端点、范围未定时更新预览
        if self._state.anchor_date is not None:
            self._state.set_hover_date(date)
            self._render_months()

    # ---- 公共 API -----------------------------------------------------

    def value(self) -> Optional[Tuple[CalendarDate, CalendarDate]]:
        return self._state.range_value

    def set_value(self, value: Optional[Tuple[CalendarDate, CalendarDate]]) -> None:
        if value is not None:
            self._state.select_date(value[0])
            self._state.select_date(value[1])
