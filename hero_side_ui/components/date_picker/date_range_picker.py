"""DateRangePicker：_RangeDateField + RangeCalendar 弹层，范围写回两组段。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ..button import Button
from ..calendar import CalendarDate, RangeCalendar
from ..date_input import DateTimeValue
from ._range_field import RangeValue, _RangeDateField

_CALENDAR_ICON = "solar--calendar-bold"

_SELECTOR_ICON_SIZE = {"sm": 16, "md": 18, "lg": 20}
_SELECTOR_BTN_SIZE = {"sm": 20, "md": 24, "lg": 28}

_TIME_GRANULARITIES = ("hour", "minute", "second")


class DateRangePicker(QWidget):
    """日期范围选择器：单输入框双段组 + 范围日历弹窗。

    Args:
        start_value: 开始端初始值。
        end_value: 结束端初始值。
        separator: 两组段分隔符。
        visible_months: 并排月数，范围选择常用 2。
    """

    value_changed = Signal(object)

    def __init__(
        self,
        label: str = "",
        start_value: DateTimeValue | None = None,
        end_value: DateTimeValue | None = None,
        placeholder_value: DateTimeValue | None = None,
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: str | None = None,
        label_placement: str = "inside",
        granularity: str = "day",
        hour_cycle: int | None = None,
        hide_time_zone: bool = False,
        should_force_leading_zeros: bool = True,
        min_value: DateTimeValue | None = None,
        max_value: DateTimeValue | None = None,
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
        first_day_of_week: str | None = None,
        weekday_style: str = "narrow",
        page_behavior: str = "visible",
        show_month_and_year_pickers: bool = True,
        is_date_unavailable: Callable[[CalendarDate], bool] | None = None,
        calendar_top_content: QWidget | None = None,
        calendar_bottom_content: QWidget | None = None,
        calendar_header_default_expanded: bool = False,
        # Popover 专属
        popover_placement: str = "bottom-start",
        disable_animation: bool = False,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建范围选择器：双段输入框 + 范围日历弹层。

        Args:
            label: 标签文本。
            start_value: 起始端初始值。
            end_value: 结束端初始值。
            placeholder_value: 占位段增减的起点值。
            variant: 输入框外框变体。
            color: 语义色。
            size: 尺寸档位。
            radius: 圆角档位。
            label_placement: 标签位置。
            granularity: day / hour / minute / second。
            hour_cycle: 12 / 24；None 跟随 locale。
            hide_time_zone: 隐藏时区段。
            should_force_leading_zeros: 数字段补前导零。
            min_value: 值域下界。
            max_value: 值域上界。
            locale: ICU locale 字符串。
            calendar: ICU 历法标识。
            is_disabled: 禁用。
            is_invalid: 错误态。
            is_required: 必填星号。
            is_readonly: 只读。
            full_width: 是否横向撑满。
            description: 描述文本。
            error_message: 错误提示文本。
            separator: 两组段之间的分隔符。
            selector_button_placement: 日历按钮位置 start / end。
            visible_months: 并排月数，范围选择默认 2。
            first_day_of_week: 周起点。
            weekday_style: 星期名宽度 narrow / short / long。
            page_behavior: 翻页步长策略。
            show_month_and_year_pickers: 显示月/年选择器。
            is_date_unavailable: 自定义不可用日期判定。
            calendar_top_content: 日历上方自定义内容。
            calendar_bottom_content: 日历下方自定义内容。
            calendar_header_default_expanded: 初始展开月/年选择器。
            popover_placement: 弹层方位。
            disable_animation: 关闭动画。
            theme: auto / light / dark。
            parent: Qt 父对象。

        Note:
            两端初始值都给定时才构造 init_range 传给日历；
            popover 用 event="manual" 避免与按钮 clicked 重复 toggle。
        """
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

        self._calendar = RangeCalendar(
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
            surface="popover",
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
        self._selector_btn.setFixedSize(
            _SELECTOR_BTN_SIZE.get(size, 28), _SELECTOR_BTN_SIZE.get(size, 28)
        )
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
        """点击日历按钮：切换弹层开合；禁用时忽略。"""
        if self._field.is_disabled():
            return
        if self._popover.is_open():
            self._popover.close()
        else:
            self._popover.open(near=self)

    def _on_calendar_change(self, rng: tuple[CalendarDate, CalendarDate] | None):
        """日历选定范围 → 写回两组段。

        Args:
            rng: (start, end) 日期元组；None 或空元组忽略。

        Note:
            保留已有的时间部分（with_date）；缺失端用 from_date 构造。
            两端齐全且无时间粒度时自动收起弹层。
        """
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
        """手动输入 → 同步日历高亮并对外广播。

        Args:
            value: (start, end) 当前范围；两端齐全才同步日历。

        Note:
            _syncing 守卫打断「输入 → 日历 → 输入」回环。
        """
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
        """返回当前范围。

        Returns:
            (start, end) 元组，元素可为 None。
        """
        return self._field.range_value()

    def set_range_value(self, value: RangeValue):
        """受控设置范围：同步输入框与日历并发出 value_changed。

        Args:
            value: (start, end) 元组。

        Note:
            全程标记 _syncing，避免两个方向的回调互相触发。
        """
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
        """set_range_value 的别名。

        Args:
            value: (start, end) 元组。
        """
        self.set_range_value(value)

    def clear(self):
        """清空两组段，回到占位态。"""
        self._field.clear()

    def set_is_disabled(self, disabled: bool):
        """切换禁用态并联动按钮与弹层。

        Args:
            disabled: True 时禁用输入与按钮并收起弹层。
        """
        self._field.set_is_disabled(disabled)
        self._selector_btn.setEnabled(not disabled)
        if disabled:
            self._popover.close()

    def is_disabled(self) -> bool:
        """返回是否禁用。

        Returns:
            True 表示整体禁用。
        """
        return self._field.is_disabled()

    def open_calendar(self):
        """程序化打开日历弹层（禁用时忽略）。"""
        if not self._field.is_disabled():
            self._popover.open(near=self)

    def close_calendar(self):
        """关闭日历弹层。"""
        self._popover.close()

    def is_calendar_open(self) -> bool:
        """日历弹层是否展开。

        Returns:
            True 表示弹层当前可见。
        """
        return self._popover.is_open()

    @property
    def date_field(self) -> _RangeDateField:
        """暴露内部双段输入框。

        Returns:
            组合使用的 _RangeDateField 实例。
        """
        return self._field

    @property
    def calendar_widget(self) -> RangeCalendar:
        """暴露内部范围日历组件。

        Returns:
            Popover 内的 RangeCalendar 实例。
        """
        return self._calendar
