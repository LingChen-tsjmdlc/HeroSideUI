"""Calendar 范围选择状态机（零 Qt 依赖）。

对齐 react-stately 的 useRangeCalendarState：在单选状态机基础上加入
锚点选择（第一次点设 anchor，第二次点确定另一端并自动排序）与 hover 预览
（设了 anchor 后随鼠标实时更新 highlighted_range）。

highlighted_range 同时代表「已选范围」与「预览范围」；渲染层据此为每个
cell 算 range_selection / selection_start·end / range_start·end。
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from ._date import CalendarDate
from ._state import CalendarState


class RangeCalendarState(CalendarState):
    def __init__(
        self,
        *,
        value: Optional[Tuple[CalendarDate, CalendarDate]] = None,
        **kwargs,
    ) -> None:
        # 父类的 value 是单个日期，这里改用 range，故传 None 给父类
        start_focus = value[0] if value else None
        super().__init__(value=start_focus, **kwargs)

        self._range: Optional[Tuple[CalendarDate, CalendarDate]] = value
        self._anchor: Optional[CalendarDate] = None
        self._hover: Optional[CalendarDate] = None
        # 范围版 on_change 参数是 (start, end)
        self.on_range_change: Optional[
            Callable[[Optional[Tuple[CalendarDate, CalendarDate]]], None]
        ] = None

    # ---- 只读视图 -----------------------------------------------------

    @property
    def range_value(self) -> Optional[Tuple[CalendarDate, CalendarDate]]:
        return self._range

    @property
    def anchor_date(self) -> Optional[CalendarDate]:
        return self._anchor

    def highlighted_range(self) -> Optional[Tuple[CalendarDate, CalendarDate]]:
        """已选或预览中的范围（升序）。选择中优先用 anchor+hover 预览。"""
        if self._anchor is not None:
            other = self._hover or self._anchor
            return _sorted_pair(self._anchor, other)
        return self._range

    # ---- 覆写 _GridState 协议 -----------------------------------------

    def is_range(self) -> bool:
        return True

    def selected_range(self) -> Optional[Tuple[CalendarDate, CalendarDate]]:
        return self.highlighted_range()

    def is_selected(self, date: CalendarDate) -> bool:
        rng = self.highlighted_range()
        if rng is None:
            return False
        start, end = rng
        return start <= date <= end

    @property
    def is_value_invalid(self) -> bool:
        if self._range is None:
            return False
        start, end = self._range
        for d in (start, end):
            if d < self._min or d > self._max or self.is_unavailable(d):
                return True
        return False

    # ---- 操作 ---------------------------------------------------------

    def select_date(self, date: CalendarDate) -> None:
        if self._is_disabled or self._is_readonly:
            return
        if self.is_disabled_date(date):
            return

        if self._anchor is None:
            # 第一次点：设锚点，范围尚未确定
            self._anchor = date
            self._hover = date
            self.set_focused_date(date)
            return

        # 第二次点：确定范围并排序
        start, end = _sorted_pair(self._anchor, date)
        self._range = (start, end)
        self._anchor = None
        self._hover = None
        self.set_focused_date(date)
        if self.on_range_change:
            self.on_range_change(self._range)

    def set_hover_date(self, date: Optional[CalendarDate]) -> None:
        """选择进行中（已设 anchor）时更新预览端点。"""
        if self._anchor is None:
            return
        self._hover = date


def _sorted_pair(a: CalendarDate, b: CalendarDate) -> Tuple[CalendarDate, CalendarDate]:
    return (a, b) if a <= b else (b, a)
