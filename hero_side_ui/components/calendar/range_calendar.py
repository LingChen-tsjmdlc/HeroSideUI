"""RangeCalendar：复用 Calendar 骨架换范围状态机；change 发 (start, end)。"""

from __future__ import annotations

from ._date import CalendarDate
from ._range_state import RangeCalendarState
from ._state import CalendarState
from .calendar import Calendar


class RangeCalendar(Calendar):
    def _create_state(self, *, value=None, **kwargs) -> CalendarState:
        """创建范围状态机并挂上范围变更回调。

        Args:
            value: 初始范围 (start, end)。
            **kwargs: 透传给 RangeCalendarState。

        Returns:
            已绑定 on_range_change 的 RangeCalendarState。
        """
        # value 对范围日历是 (start, end) 元组
        state = RangeCalendarState(value=value, **kwargs)
        state.on_range_change = self._on_range_change
        return state

    def _on_range_change(self, rng) -> None:
        """范围确认后整体重绘并对外发 change 信号。

        Args:
            rng: (start, end) 范围元组。
        """
        self._render_all()
        self.change.emit(rng)

    # ---- 覆盖交互：范围点击 + hover 预览 ------------------------------

    def _on_date_clicked(self, date: CalendarDate) -> None:
        """处理日期点击：交给范围状态机并刷新预览。

        Args:
            date: 被点击的日期。
        """
        self._state.select_date(date)
        # 选择进行中（已锚定第一端点）时，实时刷新网格显示预览
        self._render_months()

    def _on_date_hovered(self, date) -> None:
        """处理 hover：仅在选择进行中更新预览端点。

        Args:
            date: 当前 hover 的日期或 None。
        """
        # 仅在已锚定第一端点、范围未定时更新预览
        if self._state.anchor_date is not None:
            self._state.set_hover_date(date)
            self._render_months()

    # ---- 公共 API -----------------------------------------------------

    def value(self) -> tuple[CalendarDate, CalendarDate] | None:
        """返回当前已确认的范围。

        Returns:
            (start, end)；未确认时为 None。
        """
        return self._state.range_value

    def set_value(self, value: tuple[CalendarDate, CalendarDate] | None) -> None:
        """程序化设置范围：按两端点顺序模拟两次点击。

        Args:
            value: (start, end)；None 不做任何操作。
        """
        if value is not None:
            self._state.select_date(value[0])
            self._state.select_date(value[1])
