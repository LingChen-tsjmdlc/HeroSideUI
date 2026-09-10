"""HeroSideUI TimeInput Component — 分段时间输入。

基于 HeroUI v2 的 TimeInput 设计。TimeInput = DateInput 的时间粒度特化：
只显示 时/分/秒/AM-PM/时区 段，不含年/月/日段；外框视觉与交互
（分段聚焦、逐位输入、上下键回绕、越界标红）完全复用 DateInput。

对齐官方实现的关键决策：
    - 官方 TimeInput = DateInputGroup + DateInputField，state 换成
      useTimeFieldState（时间粒度、无日期段），主题复用 dateInput slots；
      本组件对应地继承 DateInput 并只覆写粒度与段构成。
    - granularity 仅允许 hour/minute/second，默认 minute（对齐
      react-aria 的 useTimeFieldState）。
    - 占位值默认当前时刻（对齐 react-aria：TimeField 的占位起点是
      now，而 DateField 是 today）。
    - min/max 约束只作用于时刻部分，日期部分不参与越界判定。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from ..date_input._pattern import TIME_GRANULARITIES
from ..date_input._value import DateTimeValue, now
from ..date_input.date_input import DateInput

__all__ = ["TimeInput"]


class TimeInput(DateInput):
    """HeroUI 风格的分段时间输入组件。

    与 DateInput 共享全部公共 API（value/set_value/clear/set_hour_cycle/
    set_min_value/set_max_value/…），差异仅在：

    :cvar _object_name: QSS objectName 为 "heroTimeInput"
    :cvar _valid_granularities: 仅 hour/minute/second
    :cvar _default_granularity: 默认 minute
    :cvar _include_date: 无日期段，段列表只有时间部分

    :param placeholder_value: 占位起点；默认当前时刻
    :param min_value / max_value: 时刻范围约束，越界标红不静默改写
    :param hour_cycle: 12 或 24；None 跟随 locale 习惯
    :param hide_time_zone: 隐藏时区段
    """

    _object_name = "heroTimeInput"
    _valid_granularities = TIME_GRANULARITIES
    _default_granularity = "minute"
    _include_date = False

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
        granularity: Optional[str] = None,
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
        start_content=None,
        end_content=None,
        on_start_content_click=None,
        on_end_content_click=None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        if placeholder_value is None:
            # 对齐 react-aria useTimeFieldState：占位起点是当前时刻。
            # now() 自带本机时区，这里剥掉时区，避免默认渲染出时区段
            # （HeroUI 的 TimeField 默认外观不含 PST 之类的时区文本）
            placeholder_value = now().with_fields(timezone=None)

        super().__init__(
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
            start_content=start_content,
            end_content=end_content,
            on_start_content_click=on_start_content_click,
            on_end_content_click=on_end_content_click,
            theme=theme,
            parent=parent,
        )
