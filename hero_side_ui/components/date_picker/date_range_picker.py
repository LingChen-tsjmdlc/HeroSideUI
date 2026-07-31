"""DateRangePicker 组件 — 单边框双段组输入 + RangeCalendar + Popover。

复用 _RangeDateField 提供的「一个输入框内两组段」形态，右侧槽位注入日历
按钮，弹出 RangeCalendar；范围选定后写回两组段，粒度不含时间时自动关闭。
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ..button import Button
from ..calendar import RangeCalendar
from ..calendar._date import CalendarDate
from ..date_input import DateTimeValue
from ._range_field import RangeValue, _RangeDateField

_CALENDAR_ICON = "solar--calendar-bold"

_SELECTOR_ICON_SIZE = {"sm": 16, "md": 18, "lg": 20}
_SELECTOR_BTN_SIZE = {"sm": 20, "md": 24, "lg": 28}

_TIME_GRANULARITIES = ("hour", "minute", "second")


class _PopoverRangeCalendar(RangeCalendar):
    """RangeCalendar 子类：底色与 Popover _bg_color(default) 对齐。"""

    def _apply_styles(self) -> None:
        super()._apply_styles()
        from ..calendar import _palette as pal
        from ...themes import RADIUS
        radius = int(RADIUS["lg"].rstrip("px"))
        bg = "#ffffff" if self._theme != "dark" else "#27272a"
        header_bg = pal.surface_content1(self._theme).name()
        if self._is_invalid:
            border = pal._shade("danger", 500).name()
        elif self._theme == "dark":
            border = "rgba(255, 255, 255, 0.08)"
        else:
            border = "rgba(0, 0, 0, 0.08)"
        self.setStyleSheet(
            f"#HeroCalendar {{ background: {bg}; border-radius: {radius}px;"
            f" border: 1px solid {border}; }}"
            f"#HeroCalendarHeader {{ background: {header_bg};"
            f" border-top-left-radius: {radius}px; border-top-right-radius: {radius}px; }}"
        )


class DateRangePicker(QWidget):
    """日期范围选择器：单输入框双段组 + 范围日历弹窗。

    :param start_value: 开始端初始值
    :param end_value: 结束端初始值
    :param separator: 两组段之间的分隔符
    :param visible_months: 日历同时显示的月份数，范围选择常用 2
    """

    value_changed = Signal(object)

    def __init__(
        self,
        label: str = "",
        start_value: Optional[DateTimeValue] = None,
        end_value: Optional[DateTimeValue] = None,
        placeholder_value: Optional[DateTimeValue] = None,
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: Optional[str] = None,
        label_placement: str = "inside",
        granularity: str = "day",
        hour_cycle: Optional[int] = None,
        hide_time_zone: bool = False,
        should_force_leading_zeros: bool = True,
        min_value: Optional[DateTimeValue] = None,
        max_value: Optional[DateTimeValue] = None,
        locale: str = "en_US",
        calendar: str = "gregorian",
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        is_readonly: bool = False,
        full_width: bool = True,
        description: str = "",
        error_message: str = "",
        separator: str = "–",
        selector_button_placement: str = "end",
        # RangeCalendar 专属
        visible_months: int = 2,
        first_day_of_week: Optional[str] = None,
        weekday_style: str = "narrow",
        page_behavior: str = "visible",
        show_month_and_year_pickers: bool = True,
        is_date_unavailable: Optional[Callable[[CalendarDate], bool]] = None,
        calendar_top_content: Optional[QWidget] = None,
        calendar_bottom_content: Optional[QWidget] = None,
        calendar_header_default_expanded: bool = False,
        # Popover 专属
        popover_placement: str = "bottom-start",
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("HeroDateRangePicker")

        self._has_time = granularity in _TIME_GRANULARITIES
        self._syncing = False

        self._field = _RangeDateField(
            label=label,
            value=start_value,
            end_value=end_value,
            separator=separator,
            placeholder_value=placeholder_value,
            variant=variant,
            color=color,
            size=size,
            radius=radius,
            label_placement=label_placement,
            granularity=granularity,
            hour_cycle=hour_cycle,
            hide_time_zone=hide_time_zone,
            should_force_leading_zeros=should_force_leading_zeros,
            min_value=min_value,
            max_value=max_value,
            locale=locale,
            calendar=calendar,
            is_disabled=is_disabled,
            is_invalid=is_invalid,
            is_required=is_required,
            is_readonly=is_readonly,
            full_width=full_width,
            description=description,
            error_message=error_message,
            theme=theme,
            parent=self,
        )

        init_range = None
        if start_value is not None and end_value is not None:
            init_range = (start_value.date, end_value.date)

        self._calendar = _PopoverRangeCalendar(
            value=init_range,
            min_value=min_value.date if min_value is not None else None,
            max_value=max_value.date if max_value is not None else None,
            color="primary" if color == "default" else color,
            visible_months=visible_months,
            first_day_of_week=first_day_of_week,
            weekday_style=weekday_style,
            page_behavior=page_behavior,
            show_month_and_year_pickers=show_month_and_year_pickers,
            is_date_unavailable=is_date_unavailable,
            disable_animation=disable_animation,
            top_content=calendar_top_content,
            bottom_content=calendar_bottom_content,
            is_header_default_expanded=calendar_header_default_expanded,
            identifier=calendar,
            theme=theme,
        )

        from ..popover import Popover

        self._popover = Popover(
            placement=popover_placement,
            disable_animation=disable_animation,
            close_on_scroll=False,
            trigger_scale_on_open=False,
            theme=theme,
            parent=self,
        )
        self._popover.set_content(self._calendar)

        self._selector_btn = Button(
            icon_only=True,
            icon=_CALENDAR_ICON,
            icon_size=_SELECTOR_ICON_SIZE.get(size, 18),
            radius="full",
            size="sm",
            variant="light",
            color="default",
            is_disabled=is_disabled,
            theme=theme,
            parent=self,
        )
        self._selector_btn.setFixedSize(_SELECTOR_BTN_SIZE.get(size, 28), _SELECTOR_BTN_SIZE.get(size, 28))
        self._popover.attach(self._selector_btn, event="manual")
        self._selector_btn.clicked.connect(self._on_selector_click)

        if selector_button_placement == "start":
            self._field.set_start_content(self._selector_btn)
        else:
            self._field.set_end_content(self._selector_btn)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._field)

        if not full_width:
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._calendar.change.connect(self._on_calendar_change)
        self._field.range_changed.connect(self._on_field_change)

    # ----------------------------------------------------------------
    # 内部回调
    # ----------------------------------------------------------------

    def _on_selector_click(self):
        if self._field.is_disabled():
            return
        if self._popover.is_open():
            self._popover.close()
        else:
            self._popover.open(near=self)

    def _on_calendar_change(self, rng: Optional[Tuple[CalendarDate, CalendarDate]]):
        """日历选定范围 → 写回两组段。"""
        if self._syncing or not rng:
            return
        start_cal, end_cal = rng
        if start_cal is None:
            return

        cur_start, cur_end = self._field.range_value()
        new_start = (
            cur_start.with_date(start_cal)
            if cur_start is not None
            else DateTimeValue.from_date(start_cal, has_time=self._has_time)
        )
        if end_cal is None:
            new_end = cur_end
        else:
            new_end = (
                cur_end.with_date(end_cal)
                if cur_end is not None
                else DateTimeValue.from_date(end_cal, has_time=self._has_time)
            )

        self._syncing = True
        try:
            self._field.set_range_value((new_start, new_end))
        finally:
            self._syncing = False

        self.value_changed.emit(self._field.range_value())

        if end_cal is not None and not self._has_time:
            self._popover.close()

    def _on_field_change(self, value: RangeValue):
        """手动输入 → 同步日历高亮并对外广播。"""
        if self._syncing:
            return
        start, end = value
        self._syncing = True
        try:
            if start is not None and end is not None:
                self._calendar.set_value((start.date, end.date))
        finally:
            self._syncing = False
        self.value_changed.emit(value)

    # ----------------------------------------------------------------
    # 公共 API
    # ----------------------------------------------------------------

    def value(self) -> RangeValue:
        return self._field.range_value()

    def set_range_value(self, value: RangeValue):
        start, end = value
        self._syncing = True
        try:
            self._field.set_range_value((start, end))
            if start is not None and end is not None:
                self._calendar.set_value((start.date, end.date))
        finally:
            self._syncing = False
        self.value_changed.emit(self._field.range_value())

    def set_value(self, value: RangeValue):
        self.set_range_value(value)

    def clear(self):
        self._field.clear()

    def set_is_disabled(self, disabled: bool):
        self._field.set_is_disabled(disabled)
        self._selector_btn.setEnabled(not disabled)
        if disabled:
            self._popover.close()

    def is_disabled(self) -> bool:
        return self._field.is_disabled()

    def open_calendar(self):
        if not self._field.is_disabled():
            self._popover.open(near=self)

    def close_calendar(self):
        self._popover.close()

    def is_calendar_open(self) -> bool:
        return self._popover.is_open()

    @property
    def date_field(self) -> _RangeDateField:
        return self._field

    @property
    def calendar_widget(self) -> RangeCalendar:
        return self._calendar
