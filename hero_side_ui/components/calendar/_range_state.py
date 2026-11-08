"""Calendar 范围状态机（零 Qt 依赖）：锚点选择 + hover 预览。
highlightened_range 兼指已选与预览范围。
"""

from __future__ import annotations

from collections.abc import Callable

from ._date import CalendarDate
from ._state import CalendarState


class RangeCalendarState(CalendarState):
    def __init__(
        self,
        *,
        value: tuple[CalendarDate, CalendarDate] | None = None,
        **kwargs,
    ) -> None:
        """创建范围选择状态机。

        Args:
            value: 初始范围 (start, end)；None 表示未选。
            **kwargs: 透传给 CalendarState（min/max/只读等）。

        Note:
            父类 value 是单个日期，这里改用 range，
            只把 start 传给父类做初始焦点。
        """
        # 父类的 value 是单个日期，这里改用 range，故传 None 给父类
        start_focus = value[0] if value else None
        super().__init__(value=start_focus, **kwargs)

        self._range: tuple[CalendarDate, CalendarDate] | None = value
        self._anchor: CalendarDate | None = None
        self._hover: CalendarDate | None = None
        # 范围版 on_change 参数是 (start, end)
        self.on_range_change: Callable[[tuple[CalendarDate, CalendarDate] | None], None] | None = (
            None
        )

    # ---- 只读视图 -----------------------------------------------------

    @property
    def range_value(self) -> tuple[CalendarDate, CalendarDate] | None:
        """当前已确认的范围。

        Returns:
            (start, end) 元组；未确认时为 None。
        """
        return self._range

    @property
    def anchor_date(self) -> CalendarDate | None:
        """当前锚点（第一次点击的日期）。

        Returns:
            选择进行中为锚点日期；空闲时为 None。
        """
        return self._anchor

    def highlighted_range(self) -> tuple[CalendarDate, CalendarDate] | None:
        """已选或预览中的范围（升序）。

        Returns:
            选择中优先返回 anchor + hover 的预览范围；
            否则返回已确认范围。
        """
        if self._anchor is not None:
            other = self._hover or self._anchor
            return _sorted_pair(self._anchor, other)
        return self._range

    # ---- 覆写 _GridState 协议 -----------------------------------------

    def is_range(self) -> bool:
        """标识本状态机为范围模式。

        Returns:
            恒 True。
        """
        return True

    def selected_range(self) -> tuple[CalendarDate, CalendarDate] | None:
        """网格协议：当前高亮范围。

        Returns:
            highlighted_range 的结果。
        """
        return self.highlighted_range()

    def is_selected(self, date: CalendarDate) -> bool:
        """判断日期是否落在高亮范围内。

        Args:
            date: 目标日期。

        Returns:
            start <= date <= end 时为 True。
        """
        rng = self.highlighted_range()
        if rng is None:
            return False
        start, end = rng
        return start <= date <= end

    @property
    def is_value_invalid(self) -> bool:
        """已确认范围是否越界或含不可用日期。

        Returns:
            任一端点越出 [min, max] 或 unavailable 时为 True。
        """
        if self._range is None:
            return False
        start, end = self._range
        return any(d < self._min or d > self._max or self.is_unavailable(d) for d in (start, end))

    # ---- 操作 ---------------------------------------------------------

    def select_date(self, date: CalendarDate) -> None:
        """处理点击：第一次设锚点，第二次确认范围。

        Args:
            date: 被点击的日期。

        Note:
            禁用 / 只读 / 禁用日期直接忽略；第二次点击后按升序
            存范围并触发 on_range_change 回调。
        """
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

    def set_hover_date(self, date: CalendarDate | None) -> None:
        """选择进行中（已设 anchor）时更新预览端点。

        Args:
            date: 当前 hover 的日期；None 清空预览。
        """
        if self._anchor is None:
            return
        self._hover = date


def _sorted_pair(a: CalendarDate, b: CalendarDate) -> tuple[CalendarDate, CalendarDate]:
    """按升序返回两个日期。

    Args:
        a: 第一个日期。
        b: 第二个日期。

    Returns:
        (小, 大) 顺序的元组。
    """
    return (a, b) if a <= b else (b, a)
