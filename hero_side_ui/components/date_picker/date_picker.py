"""DatePicker 组件 — DateInput + Calendar + Popover 的组合。

以 DateInput 为基底，在 start/end 槽位注入日历图标按钮；点击按钮 toggle
Popover 弹出 Calendar，选择日期后写回 DateInput。粒度不含时间时选完即关闭。
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ..button import Button
from ..calendar import Calendar
from ..calendar._date import CalendarDate
from ..date_input import DateTimeValue
from ..date_input.date_input import DateInput
from ..popover import Popover

_CALENDAR_ICON = "solar--calendar-bold"

# 选择器按钮图标边长，按输入框尺寸档位取值
_SELECTOR_ICON_SIZE = {"sm": 16, "md": 18, "lg": 20}

# 选择器按钮固定边长（正方形），必须 ≤ DateInput 内部可用高度
# sm: wrapper=32 padding_y=4 → 可用 24；md: wrapper=40 padding_y=6 → 可用 28；lg: wrapper=48 padding_y=8 → 可用 32
_SELECTOR_BTN_SIZE = {"sm": 20, "md": 24, "lg": 28}

_TIME_GRANULARITIES = ("hour", "minute", "second")


# Popover 内嵌用 Calendar 子类：底色与 Popover 的 _bg_color(default) 对齐，
# 避免 surface_base(dark #0b0d12) 与 Popover 实心底(dark #27272a) 冲突透出。
class _PopoverCalendar(Calendar):
    def _apply_styles(self) -> None:
        super()._apply_styles()
        # 覆写日期区底色为 Popover 同款（light #ffffff / dark #27272a）
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


class DatePicker(QWidget):
    """日期选择器：分段输入 + 日历弹窗。

    :param value: 初始值
    :param granularity: 精度，day/hour/minute/second
    :param selector_button_placement: 日历按钮位置，"start" 或 "end"
    :param visible_months: 日历同时显示的月份数
    :param show_month_and_year_pickers: 显示月/年选择器（仅单月生效）
    :param calendar_header_default_expanded: 月/年选择器默认展开
    :param popover_placement: 弹层相对按钮的方位
    """

    value_changed = Signal(object)

    def __init__(
        self,
        label: str = "",
        value: Optional[DateTimeValue] = None,
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
        selector_button_placement: str = "end",
        # Calendar 专属
        visible_months: int = 1,
        first_day_of_week: Optional[str] = None,
        weekday_style: str = "narrow",
        page_behavior: str = "visible",
        show_month_and_year_pickers: bool = False,
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
        self.setObjectName("HeroDatePicker")

        self._has_time = granularity in _TIME_GRANULARITIES
        self._syncing = False

        self._date_input = DateInput(
            label=label,
            value=value,
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

        self._calendar = _PopoverCalendar(
            value=value.date if value is not None else None,
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

        self._popover = Popover(
            placement=popover_placement,
            disable_animation=disable_animation,
            close_on_scroll=False,
            trigger_scale_on_open=False,
            theme=theme,
            parent=self,
        )
        self._popover.set_content(self._calendar)

        icon_px = _SELECTOR_ICON_SIZE.get(size, 18)
        btn_side = _SELECTOR_BTN_SIZE.get(size, 28)
        self._selector_btn = Button(
            icon_only=True,
            icon=_CALENDAR_ICON,
            icon_size=icon_px,
            radius="full",
            size="sm",
            variant="light",
            color="default",
            is_disabled=is_disabled,
            theme=theme,
            parent=self,
        )
        self._selector_btn.setFixedSize(btn_side, btn_side)
        # event="manual"：只登记 trigger 供 open() 定位，点击由 clicked 驱动，
        # 避免 Popover 的事件过滤器与按钮自身的 clicked 重复 toggle
        self._popover.attach(self._selector_btn, event="manual")
        self._selector_btn.clicked.connect(self._on_selector_click)

        if selector_button_placement == "start":
            self._date_input.set_start_content(self._selector_btn)
        else:
            self._date_input.set_end_content(self._selector_btn)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._date_input)

        if not full_width:
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._calendar.change.connect(self._on_calendar_change)
        self._date_input.value_changed.connect(self._on_input_change)

    # ----------------------------------------------------------------
    # 内部回调
    # ----------------------------------------------------------------

    def _on_selector_click(self):
        if self._date_input.is_disabled():
            return
        if self._popover.is_open():
            self._popover.close()
        else:
            self._popover.open(near=self)

    def _on_calendar_change(self, cal_date: Optional[CalendarDate]):
        """日历选中 → 写回 DateInput。"""
        if self._syncing or cal_date is None:
            return
        self._syncing = True
        try:
            cur = self._date_input.value()
            if cur is None:
                self._date_input.set_value(
                    DateTimeValue.from_date(cal_date, has_time=self._has_time)
                )
            else:
                self._date_input.set_value(cur.with_date(cal_date))
        finally:
            self._syncing = False

        self.value_changed.emit(self._date_input.value())

        if not self._has_time:
            self._popover.close()

    def _on_input_change(self, dt_val: Optional[DateTimeValue]):
        """手动输入 → 同步日历高亮并对外广播。"""
        if self._syncing:
            return
        self._syncing = True
        try:
            if dt_val is not None:
                self._calendar.set_value(dt_val.date)
        finally:
            self._syncing = False
        self.value_changed.emit(dt_val)

    # ----------------------------------------------------------------
    # 公共 API
    # ----------------------------------------------------------------

    def value(self) -> Optional[DateTimeValue]:
        return self._date_input.value()

    def set_value(self, value: Optional[DateTimeValue]):
        self._syncing = True
        try:
            self._date_input.set_value(value)
            if value is not None:
                self._calendar.set_value(value.date)
        finally:
            self._syncing = False
        self.value_changed.emit(self._date_input.value())

    def clear(self):
        self._date_input.clear()

    def set_is_disabled(self, disabled: bool):
        self._date_input.set_is_disabled(disabled)
        self._selector_btn.setEnabled(not disabled)
        if disabled:
            self._popover.close()

    def is_disabled(self) -> bool:
        return self._date_input.is_disabled()

    def open_calendar(self):
        if not self._date_input.is_disabled():
            self._popover.open(near=self)

    def close_calendar(self):
        self._popover.close()

    def is_calendar_open(self) -> bool:
        return self._popover.is_open()

    @property
    def date_input(self) -> DateInput:
        return self._date_input

    @property
    def calendar_widget(self) -> Calendar:
        return self._calendar
