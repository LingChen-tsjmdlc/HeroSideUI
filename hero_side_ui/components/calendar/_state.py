"""Calendar 单选状态机（零 Qt 依赖）。

对齐 react-stately 的 useCalendarState：维护 focused_date（当前焦点，未必选中）、
value（选中值）、visible_range（当前首月起点），以及翻页 / 选择 / 边界判定。
渲染层只读此状态，通过回调把用户操作转成 state 方法调用。

focused_date 与 value 分离：键盘方向键只动 focused_date（触发 focus_change），
按 Enter/Space 才 select（触发 value change）。
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from ._date import (
    CalendarDate,
    clamp_date,
    normalize_first_day_of_week,
    weeks_in_month,
)

# 默认可选边界，对齐 HeroUI（1900 ~ 2099）
_DEFAULT_MIN = CalendarDate(1900, 1, 1)
_DEFAULT_MAX = CalendarDate(2099, 12, 31)


class CalendarState:
    def __init__(
        self,
        *,
        value: Optional[CalendarDate] = None,
        min_value: Optional[CalendarDate] = None,
        max_value: Optional[CalendarDate] = None,
        visible_months: int = 1,
        page_behavior: str = "visible",  # "visible" | "single"
        first_day_of_week: Optional[str] = None,
        is_disabled: bool = False,
        is_readonly: bool = False,
        is_unavailable_fn: Optional[Callable[[CalendarDate], bool]] = None,
        identifier: str = "gregorian",
    ) -> None:
        self._identifier = identifier
        self._min = min_value or _DEFAULT_MIN
        self._max = max_value or _DEFAULT_MAX
        self.visible_months = max(1, min(3, visible_months))
        self.page_behavior = page_behavior
        self.first_day_of_week = normalize_first_day_of_week(first_day_of_week)
        self._is_disabled = is_disabled
        self._is_readonly = is_readonly
        self._is_unavailable_fn = is_unavailable_fn

        self._value = value
        anchor = value or CalendarDate.today(identifier)
        self._focused = clamp_date(anchor, self._min, self._max)
        self._visible_start = self._focused.first_of_month()

        # 回调（渲染层注入）
        self.on_change: Optional[Callable[[Optional[CalendarDate]], None]] = None
        self.on_focus_change: Optional[Callable[[CalendarDate], None]] = None

    # ---- 只读视图 -----------------------------------------------------

    @property
    def value(self) -> Optional[CalendarDate]:
        return self._value

    @property
    def focused_date(self) -> CalendarDate:
        return self._focused

    @property
    def visible_range_start(self) -> CalendarDate:
        return self._visible_start

    @property
    def min_value(self) -> CalendarDate:
        return self._min

    @property
    def max_value(self) -> CalendarDate:
        return self._max

    @property
    def identifier(self) -> str:
        return self._identifier

    def visible_month_starts(self) -> List[CalendarDate]:
        """当前可见的每个月的 1 号（用于渲染多月并排）。"""
        return [self._visible_start.add(months=i) for i in range(self.visible_months)]

    # ---- _GridState 协议 ----------------------------------------------

    def is_range(self) -> bool:
        return False

    def selected_range(self) -> Optional[Tuple[CalendarDate, CalendarDate]]:
        return None

    def is_readonly(self) -> bool:
        return self._is_readonly

    def is_selected(self, date: CalendarDate) -> bool:
        return self._value is not None and self._value.is_same_day(date)

    def is_unavailable(self, date: CalendarDate) -> bool:
        return bool(self._is_unavailable_fn and self._is_unavailable_fn(date))

    def is_disabled_date(self, date: CalendarDate) -> bool:
        if self._is_disabled:
            return True
        if date < self._min or date > self._max:
            return True
        return self.is_unavailable(date)

    @property
    def is_value_invalid(self) -> bool:
        v = self._value
        if v is None:
            return False
        return v < self._min or v > self._max or self.is_unavailable(v)

    # ---- 操作 ---------------------------------------------------------

    def select_date(self, date: CalendarDate) -> None:
        if self._is_disabled or self._is_readonly:
            return
        if self.is_disabled_date(date):
            return
        self._value = date
        self._set_focused(date, notify=True)
        if self.on_change:
            self.on_change(self._value)

    def set_focused_date(self, date: CalendarDate) -> None:
        self._set_focused(clamp_date(date, self._min, self._max), notify=True)

    def _set_focused(self, date: CalendarDate, *, notify: bool) -> None:
        changed = not date.is_same_day(self._focused)
        self._focused = date
        # 焦点移出可见范围时，滚动可见窗口跟随
        if not self._focused_visible():
            self._visible_start = date.first_of_month()
        if notify and changed and self.on_focus_change:
            self.on_focus_change(self._focused)

    def _focused_visible(self) -> bool:
        first = self._visible_start
        last = self._visible_start.add(months=self.visible_months - 1).last_of_month()
        return first <= self._focused <= last

    # ---- 翻页 ---------------------------------------------------------

    def _page_step(self) -> int:
        return self.visible_months if self.page_behavior == "visible" else 1

    def focus_next_page(self) -> None:
        step = self._page_step()
        self._visible_start = self._visible_start.add(months=step)
        self._set_focused(clamp_date(self._focused.add(months=step), self._min, self._max),
                          notify=True)

    def focus_previous_page(self) -> None:
        step = self._page_step()
        self._visible_start = self._visible_start.add(months=-step)
        self._set_focused(clamp_date(self._focused.add(months=-step), self._min, self._max),
                          notify=True)

    def can_page_next(self) -> bool:
        return self._visible_start.add(months=self.visible_months).first_of_month() <= self._max

    def can_page_previous(self) -> bool:
        return self._visible_start.add(months=-1).last_of_month() >= self._min

    def weeks_in_visible_month(self, month_start: CalendarDate) -> int:
        return weeks_in_month(month_start, self.first_day_of_week)
