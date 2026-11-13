"""Calendar 网格切分与状态判定（零 Qt 依赖）：月切周、逐格算 data-* 状态。
selection_start/end 是范围逻辑端点；range_start/end 是行内视觉端点。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..._shared.dates import CalendarDate, weeks_in_month


class _GridState(Protocol):
    """网格计算所需的状态只读视图。

    单选 state 与范围 state 都实现该协议，compute_cell_state 只依赖
    这组只读接口，不关心具体持有者。
    """

    first_day_of_week: int

    def is_selected(self, date: CalendarDate) -> bool: ...
    def is_disabled_date(self, date: CalendarDate) -> bool: ...
    def is_unavailable(self, date: CalendarDate) -> bool: ...
    def is_readonly(self) -> bool: ...
    def selected_range(self) -> tuple | None: ...  # (start, end) 或 None
    def is_range(self) -> bool: ...


@dataclass(frozen=True)
class CellState:
    """单个日期格子的完整视觉状态。

    Attributes:
        date: 该格日期；None 表示空占位格。
        is_selected: 是否选中（禁用格不判选中）。
        is_disabled: 是否禁用（月外或业务禁用）。
        is_unavailable: 是否不可用（画删除线）。
        is_outside_month: 是否月外补位格。
        is_today: 是否今天（仅本月内）。
        is_readonly: 组件是否只读。
        is_range_selection: 是否处于范围选中（含中间格）。
        is_selection_start: 是否范围逻辑起点。
        is_selection_end: 是否范围逻辑终点。
        is_range_start: 是否行内视觉起点（连接背景左收口）。
        is_range_end: 是否行内视觉终点（连接背景右收口）。
    """

    date: CalendarDate | None
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
        """是否为空占位格。

        Returns:
            date 为 None 时为 True。
        """
        return self.date is None

    @property
    def label(self) -> str:
        """格子的显示文本。

        Returns:
            日号字符串；空格返回空串。
        """
        return "" if self.date is None else str(self.date.day)


def get_dates_in_week(
    start_date: CalendarDate, week_index: int, first_day_of_week: int
) -> list[CalendarDate | None]:
    """返回该月第 week_index 周的 7 个日期。

    Args:
        start_date: 当月任一天。
        week_index: 周序号（0 起）。
        first_day_of_week: 周起点（ICU weekday 常量）。

    Returns:
        一周 7 个日期；首尾行空档用相邻月日期补齐（标记 outside
        淡显不可选），日历恒为完整 7 列矩形。
    """
    first = start_date.first_of_month()
    lead = (first.weekday - first_day_of_week) % 7

    result: list[CalendarDate | None] = []
    for col in range(7):
        offset = week_index * 7 + col - lead  # 相对本月首日的天数偏移（可负 / 可超月末）
        result.append(first.add(days=offset))
    return result


def get_weeks(start_date: CalendarDate, first_day_of_week: int) -> list[list[CalendarDate | None]]:
    """把整月切成 [周][7] 的日期矩阵。

    Args:
        start_date: 当月任一天。
        first_day_of_week: 周起点（ICU weekday 常量）。

    Returns:
        weeks_in_month 行、每行 7 列的日期（或 None）嵌套列表。
    """
    n = weeks_in_month(start_date, first_day_of_week)
    return [get_dates_in_week(start_date, w, first_day_of_week) for w in range(n)]


def compute_cell_state(
    date: CalendarDate | None, current_month: CalendarDate, state: _GridState, today: CalendarDate
) -> CellState:
    """算出单个 cell 的全部状态位。

    Args:
        date: 该格日期；None 直接返回空态。
        current_month: 当前展示月（判断月外）。
        state: 实现 _GridState 协议的状态视图。
        today: 今天的日期。

    Returns:
        含单选位与范围位的 CellState；范围态额外算逻辑端点
        （selection_start/end）与每行视觉端点（range_start/end）。
    """
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
    prev_blocked = (
        not date.is_same_month(prev_day)
        or state.is_unavailable(prev_day)
        or start.is_same_day(date)
    )
    next_blocked = (
        not date.is_same_month(next_day) or state.is_unavailable(next_day) or end.is_same_day(date)
    )

    return CellState(
        **common,
        is_range_selection=True,
        is_selection_start=date.is_same_day(start),
        is_selection_end=date.is_same_day(end),
        is_range_start=(dow == first_col(state.first_day_of_week) or date.day == 1 or prev_blocked),
        is_range_end=(
            dow == last_col(state.first_day_of_week)
            or date.day == date.days_in_month
            or next_blocked
        ),
    )


def first_col(first_day_of_week: int) -> int:
    """本周第一列对应的 ICU weekday。

    Args:
        first_day_of_week: 周起点常量。

    Returns:
        周起点本身（第一列即周起点）。
    """
    return first_day_of_week


def last_col(first_day_of_week: int) -> int:
    """本周最后一列对应的 ICU weekday。

    Args:
        first_day_of_week: 周起点常量。

    Returns:
        (起点 + 6 天) 折算回 1~7 的 ICU weekday。
    """
    return (first_day_of_week + 5) % 7 + 1
