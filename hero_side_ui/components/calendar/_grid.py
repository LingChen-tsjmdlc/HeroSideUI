"""Calendar 网格切分与单元格状态判定（零 Qt 依赖）。

对齐 react-aria 的 getDatesInWeek / useCalendarCell：
  - 把一个月切成若干周（每周 7 格，溢出补 None）。
  - 为每个日期算出渲染层需要的全部状态位（data-* 语义）。

两套「起止」语义务必分清：
  - selection_start/end：整个选中范围唯一的两个逻辑端点。
  - range_start/end：每一行的视觉端点（行首/行尾/被 unavailable 打断处），
    渲染层用它决定左右圆角；中间格靠 range_selection 画方形连接背景。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from ._date import SAT, SUN, CalendarDate, weeks_in_month


class _GridState(Protocol):
    """网格计算所需的状态只读视图，单选/范围 state 都实现它。"""

    first_day_of_week: int

    def is_selected(self, date: CalendarDate) -> bool: ...
    def is_disabled_date(self, date: CalendarDate) -> bool: ...
    def is_unavailable(self, date: CalendarDate) -> bool: ...
    def is_readonly(self) -> bool: ...
    def selected_range(self) -> Optional[tuple]: ...  # (start, end) 或 None
    def is_range(self) -> bool: ...


@dataclass(frozen=True)
class CellState:
    """单个日期格子的完整视觉状态。date 为 None 表示空占位格。"""

    date: Optional[CalendarDate]
    is_selected: bool = False
    is_disabled: bool = False
    is_unavailable: bool = False
    is_outside_month: bool = False
    is_today: bool = False
    is_readonly: bool = False
    # 范围专用
    is_range_selection: bool = False
    is_selection_start: bool = False
    is_selection_end: bool = False
    is_range_start: bool = False
    is_range_end: bool = False

    @property
    def is_empty(self) -> bool:
        return self.date is None

    @property
    def label(self) -> str:
        return "" if self.date is None else str(self.date.day)


def get_dates_in_week(start_date: CalendarDate, week_index: int,
                      first_day_of_week: int) -> List[Optional[CalendarDate]]:
    """返回该月第 week_index 周的 7 个日期。

    首尾行的本月外空档用相邻月的实际日期补齐（上月末尾 / 下月开头），
    这些日期在 compute_cell_state 里标记 is_outside_month=True，渲染层淡色显示、
    不可选。对齐 HeroUI：日历始终是完整的 7 列矩形，无空洞。
    """
    first = start_date.first_of_month()
    lead = (first.weekday - first_day_of_week) % 7

    result: List[Optional[CalendarDate]] = []
    for col in range(7):
        offset = week_index * 7 + col - lead  # 相对本月首日的天数偏移（可负 / 可超月末）
        result.append(first.add(days=offset))
    return result


def get_weeks(start_date: CalendarDate, first_day_of_week: int) -> List[List[Optional[CalendarDate]]]:
    """把整月切成 [周][7] 的日期矩阵。"""
    n = weeks_in_month(start_date, first_day_of_week)
    return [get_dates_in_week(start_date, w, first_day_of_week) for w in range(n)]


def compute_cell_state(date: Optional[CalendarDate], current_month: CalendarDate,
                       state: _GridState, today: CalendarDate) -> CellState:
    """算出单个 cell 的全部状态位。"""
    if date is None:
        return CellState(date=None)

    outside = not date.is_same_month(current_month)
    unavailable = state.is_unavailable(date)
    disabled = outside or state.is_disabled_date(date)
    selected = (not disabled) and state.is_selected(date)
    readonly = state.is_readonly()

    common = dict(
        date=date,
        is_selected=selected,
        is_disabled=disabled,
        is_unavailable=unavailable,
        is_outside_month=outside,
        is_today=date.is_same_day(today) and not outside,
        is_readonly=readonly,
    )

    if not (state.is_range() and selected):
        return CellState(**common)

    # ---- 范围态：算逻辑端点 + 每行视觉端点 ----
    rng = state.selected_range()
    if rng is None:
        return CellState(**common)
    start, end = rng
    dow = date.weekday

    prev_day = date.add(days=-1)
    next_day = date.add(days=1)
    prev_blocked = (not date.is_same_month(prev_day) or
                    state.is_unavailable(prev_day) or start.is_same_day(date))
    next_blocked = (not date.is_same_month(next_day) or
                    state.is_unavailable(next_day) or end.is_same_day(date))

    return CellState(
        **common,
        is_range_selection=True,
        is_selection_start=date.is_same_day(start),
        is_selection_end=date.is_same_day(end),
        is_range_start=(dow == first_col(state.first_day_of_week) or
                        date.day == 1 or prev_blocked),
        is_range_end=(dow == last_col(state.first_day_of_week) or
                      date.day == date.days_in_month or next_blocked),
    )


def first_col(first_day_of_week: int) -> int:
    """本周第一列对应的 ICU weekday。"""
    return first_day_of_week


def last_col(first_day_of_week: int) -> int:
    """本周最后一列对应的 ICU weekday。"""
    return (first_day_of_week + 5) % 7 + 1
