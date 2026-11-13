"""DatePicker：DateInput + 日历按钮 + Popover(Calendar)，选完写回。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from ..button import Button
from ..calendar import Calendar, CalendarDate
from ..date_input import DateInput, DateTimeValue
from ..popover import Popover

_CALENDAR_ICON = "solar--calendar-bold"

# 选择器按钮图标边长，按输入框尺寸档位取值
_SELECTOR_ICON_SIZE = {"sm": 16, "md": 18, "lg": 20}

# 选择器按钮固定边长（正方形），必须 ≤ DateInput 内部可用高度
# sm: wrapper=32 padding_y=4 → 可用 24；md: wrapper=40 padding_y=6 → 可用 28；lg: wrapper=48 padding_y=8 → 可用 32
_SELECTOR_BTN_SIZE = {"sm": 20, "md": 24, "lg": 28}

_TIME_GRANULARITIES = ("hour", "minute", "second")


class DatePicker(QWidget):
    """日期选择器：分段输入 + 日历弹窗。

    Args:
        value: 初始值。
        granularity: day/hour/minute/second。
        selector_button_placement: 日历按钮位置 start/end。
        visible_months: 日历并排月数。
        show_month_and_year_pickers: 显示月/年选择器（仅单月）。
        popover_placement: 弹层方位。
    """

    value_changed = Signal(object)

    def __init__(
        self,
        label: str = "",
        value: DateTimeValue | None = None,
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
        selector_button_placement: str = "end",
        # Calendar 专属
        visible_months: int = 1,
        first_day_of_week: str | None = None,
        weekday_style: str = "narrow",
        page_behavior: str = "visible",
        show_month_and_year_pickers: bool = False,
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
        """创建日期选择器：DateInput + 日历按钮 + Popover(Calendar)。

        Args:
            label: 标签文本。
            value: 初始值。
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
            selector_button_placement: 日历按钮位置 start / end。
            visible_months: 日历并排月数。
            first_day_of_week: 周起点。
            weekday_style: 星期名宽度 narrow / short / long。
            page_behavior: 翻页步长策略。
            show_month_and_year_pickers: 显示月/年选择器（仅单月）。
            is_date_unavailable: 自定义不可用日期判定。
            calendar_top_content: 日历上方自定义内容。
            calendar_bottom_content: 日历下方自定义内容。
            calendar_header_default_expanded: 初始展开月/年选择器。
            popover_placement: 弹层方位。
            disable_animation: 关闭动画。
            theme: auto / light / dark。
            parent: Qt 父对象。

        Note:
            popover attach 用 event="manual"，只登记 trigger 供定位，
            点击由按钮 clicked 驱动，避免与 Popover 事件过滤器重复 toggle。
        """
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

        self._calendar = Calendar(
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
            surface="popover",
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
        """点击日历按钮：切换弹层开合；禁用时忽略。"""
        if self._date_input.is_disabled():
            return
        if self._popover.is_open():
            self._popover.close()
        else:
            self._popover.open(near=self)

    def _on_calendar_change(self, cal_date: CalendarDate | None):
        """日历选中 → 写回 DateInput。

        Args:
            cal_date: 新选中的日期；None 忽略。

        Note:
            _syncing 守卫防止写回触发的 value_changed 再反向同步；
            纯日期粒度（无时间）选完自动收起弹层。
        """
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

    def _on_input_change(self, dt_val: DateTimeValue | None):
        """手动输入 → 同步日历高亮并对外广播。

        Args:
            dt_val: 输入框当前值；None 时不改日历。

        Note:
            _syncing 守卫打断「输入 → 日历 → 输入」回环。
        """
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

    def value(self) -> DateTimeValue | None:
        """返回当前值。

        Returns:
            DateInput 的值对象；未填满时为 None。
        """
        return self._date_input.value()

    def set_value(self, value: DateTimeValue | None):
        """受控赋值：同步输入框与日历并发出 value_changed。

        Args:
            value: 新值；None 清空输入框。

        Note:
            全程标记 _syncing，避免两个方向的回调互相触发。
        """
        self._syncing = True
        try:
            self._date_input.set_value(value)
            if value is not None:
                self._calendar.set_value(value.date)
        finally:
            self._syncing = False
        self.value_changed.emit(self._date_input.value())

    def clear(self):
        """清空输入框（回到全部占位段）。"""
        self._date_input.clear()

    def set_is_disabled(self, disabled: bool):
        """切换禁用态并联动按钮与弹层。

        Args:
            disabled: True 时禁用输入与按钮并收起弹层。
        """
        self._date_input.set_is_disabled(disabled)
        self._selector_btn.setEnabled(not disabled)
        if disabled:
            self._popover.close()

    def is_disabled(self) -> bool:
        """返回是否禁用。

        Returns:
            True 表示整体禁用。
        """
        return self._date_input.is_disabled()

    def open_calendar(self):
        """程序化打开日历弹层（禁用时忽略）。"""
        if not self._date_input.is_disabled():
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
    def date_input(self) -> DateInput:
        """暴露内部分段输入框。

        Returns:
            组合使用的 DateInput 实例。
        """
        return self._date_input

    @property
    def calendar_widget(self) -> Calendar:
        """暴露内部日历组件。

        Returns:
            Popover 内的 Calendar 实例。
        """
        return self._calendar
