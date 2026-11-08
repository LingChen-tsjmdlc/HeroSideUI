"""Calendar 单选状态机（零 Qt 依赖）：focused_date 与 value 分离。
方向键动焦点，Enter/Space 才选中。
"""

from __future__ import annotations

from collections.abc import Callable

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
        value: CalendarDate | None = None,
        min_value: CalendarDate | None = None,
        max_value: CalendarDate | None = None,
        visible_months: int = 1,
        page_behavior: str = "visible",  # "visible" | "single"
        first_day_of_week: str | None = None,
        is_disabled: bool = False,
        is_readonly: bool = False,
        is_unavailable_fn: Callable[[CalendarDate], bool] | None = None,
        identifier: str = "gregorian",
    ) -> None:
        """创建单选状态机。

        Args:
            value: 初始选中日期。
            min_value: 可选下界；None 取 1900-01-01。
            max_value: 可选上界；None 取 2099-12-31。
            visible_months: 并排可见月数（钳制 1~3）。
            page_behavior: visible 按可见月数翻页 / single 一次一个月。
            first_day_of_week: 周起点（sun/mon/...）；None 默认周日。
            is_disabled: 整体禁用。
            is_readonly: 只读（可导航不可选中）。
            is_unavailable_fn: 自定义不可用判定函数。
            identifier: ICU 历法标识，默认 gregorian。

        Note:
            focused_date 与 value 分离：方向键只动焦点，
            Enter/Space 才选中；初始焦点锚定在 value 或今天。
        """
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
        self.on_change: Callable[[CalendarDate | None], None] | None = None
        self.on_focus_change: Callable[[CalendarDate], None] | None = None

    # ---- 只读视图 -----------------------------------------------------

    @property
    def value(self) -> CalendarDate | None:
        """当前选中的日期。

        Returns:
            已选日期；未选中时为 None。
        """
        return self._value

    @property
    def focused_date(self) -> CalendarDate:
        """当前焦点日期。

        Returns:
            键盘导航的焦点；与 value 分离。
        """
        return self._focused

    @property
    def visible_range_start(self) -> CalendarDate:
        """可见窗口首月的 1 号。

        Returns:
            当前可见范围的起始月首日。
        """
        return self._visible_start

    @property
    def min_value(self) -> CalendarDate:
        """可选下界。

        Returns:
            钳制后的最小可选日期。
        """
        return self._min

    @property
    def max_value(self) -> CalendarDate:
        """可选上界。

        Returns:
            钳制后的最大可选日期。
        """
        return self._max

    @property
    def identifier(self) -> str:
        """ICU 历法标识。

        Returns:
            如 gregorian / islamic 等。
        """
        return self._identifier

    def visible_month_starts(self) -> list[CalendarDate]:
        """当前可见的每个月的 1 号。

        Returns:
            用于渲染多月并排的月首日列表。
        """
        return [self._visible_start.add(months=i) for i in range(self.visible_months)]

    # ---- _GridState 协议 ----------------------------------------------

    def is_range(self) -> bool:
        """是否范围模式。

        Returns:
            单选状态机恒 False。
        """
        return False

    def selected_range(self) -> tuple[CalendarDate, CalendarDate] | None:
        """网格协议：高亮范围。

        Returns:
            单选无范围，恒 None。
        """
        return None

    def is_readonly(self) -> bool:
        """是否只读。

        Returns:
            True 时可导航但不可选中。
        """
        return self._is_readonly

    def is_selected(self, date: CalendarDate) -> bool:
        """判断日期是否为当前选中值。

        Args:
            date: 目标日期。

        Returns:
            与 value 同日时为 True。
        """
        return self._value is not None and self._value.is_same_day(date)

    def is_unavailable(self, date: CalendarDate) -> bool:
        """判断日期是否不可用（画删除线）。

        Args:
            date: 目标日期。

        Returns:
            自定义判定函数的结果；未注入时为 False。
        """
        return bool(self._is_unavailable_fn and self._is_unavailable_fn(date))

    def is_disabled_date(self, date: CalendarDate) -> bool:
        """判断日期是否禁选。

        Args:
            date: 目标日期。

        Returns:
            整体禁用、越出 [min, max] 或 unavailable 任一命中即 True。
        """
        if self._is_disabled:
            return True
        if date < self._min or date > self._max:
            return True
        return self.is_unavailable(date)

    @property
    def is_value_invalid(self) -> bool:
        """当前值是否越界或不可用。

        Returns:
            value 越出 [min, max] 或 unavailable 时为 True。
        """
        v = self._value
        if v is None:
            return False
        return v < self._min or v > self._max or self.is_unavailable(v)

    # ---- 操作 ---------------------------------------------------------

    def select_date(self, date: CalendarDate) -> None:
        """选中日期并移动焦点。

        Args:
            date: 目标日期。

        Note:
            禁用 / 只读 / 禁选日期直接忽略；成功后触发 on_change。
        """
        if self._is_disabled or self._is_readonly:
            return
        if self.is_disabled_date(date):
            return
        self._value = date
        self._set_focused(date, notify=True)
        if self.on_change:
            self.on_change(self._value)

    def set_focused_date(self, date: CalendarDate) -> None:
        """移动焦点到指定日期（钳制到可选区间）。

        Args:
            date: 目标焦点日期。
        """
        self._set_focused(clamp_date(date, self._min, self._max), notify=True)

    def _set_focused(self, date: CalendarDate, *, notify: bool) -> None:
        """写焦点并在移出可见窗口时跟随滚动。

        Args:
            date: 新焦点（调用方负责钳制）。
            notify: 是否在焦点变化时触发 on_focus_change。
        """
        changed = not date.is_same_day(self._focused)
        self._focused = date
        # 焦点移出可见范围时，滚动可见窗口跟随
        if not self._focused_visible():
            self._visible_start = date.first_of_month()
        if notify and changed and self.on_focus_change:
            self.on_focus_change(self._focused)

    def _focused_visible(self) -> bool:
        """焦点是否在当前可见窗口内。

        Returns:
            焦点落在首月 1 号到末月月底之间时为 True。
        """
        first = self._visible_start
        last = self._visible_start.add(months=self.visible_months - 1).last_of_month()
        return first <= self._focused <= last

    # ---- 翻页 ---------------------------------------------------------

    def _page_step(self) -> int:
        """翻页步长（月数）。

        Returns:
            visible 模式为可见月数，single 模式为 1。
        """
        return self.visible_months if self.page_behavior == "visible" else 1

    def focus_next_page(self) -> None:
        """向后翻一页并同步焦点。"""
        step = self._page_step()
        self._visible_start = self._visible_start.add(months=step)
        self._set_focused(
            clamp_date(self._focused.add(months=step), self._min, self._max), notify=True
        )

    def focus_previous_page(self) -> None:
        """向前翻一页并同步焦点。"""
        step = self._page_step()
        self._visible_start = self._visible_start.add(months=-step)
        self._set_focused(
            clamp_date(self._focused.add(months=-step), self._min, self._max), notify=True
        )

    def can_page_next(self) -> bool:
        """是否还能向后翻页。

        Returns:
            下一窗口首月不超上界时为 True。
        """
        return self._visible_start.add(months=self.visible_months).first_of_month() <= self._max

    def can_page_previous(self) -> bool:
        """是否还能向前翻页。

        Returns:
            前一个月的月底不早于下界时为 True。
        """
        return self._visible_start.add(months=-1).last_of_month() >= self._min

    def weeks_in_visible_month(self, month_start: CalendarDate) -> int:
        """指定月按周起点需要几行。

        Args:
            month_start: 目标月任一天。

        Returns:
            4~6 的行数。
        """
        return weeks_in_month(month_start, self.first_day_of_week)
