"""TimeInput：DateInput 的时间粒度特化，只含时/分/秒/AM-PM/时区段。

granularity 仅 hour/minute/second（默认 minute）；占位值默认当前时刻；
min/max 只约束时刻部分。对齐官方 useTimeFieldState。
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..._shared.dates import TIME_GRANULARITIES, DateTimeValue, now
from ..date_input import DateInput

__all__ = ["TimeInput"]


class TimeInput(DateInput):
    """HeroUI 风格分段时间输入，与 DateInput 共享全部公共 API。

    Note:
        覆写四个类属性特化：_object_name="heroTimeInput"、粒度仅时间档、
        默认 minute、无日期段。
    """

    _object_name = "heroTimeInput"
    _valid_granularities = TIME_GRANULARITIES
    _default_granularity = "minute"
    _include_date = False

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
        granularity: str | None = None,
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
        start_content=None,
        end_content=None,
        on_start_content_click=None,
        on_end_content_click=None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """构建时间输入，未给占位值时以当前时刻（剥离时区）作为占位起点。

        Note:
            placeholder_value 为空时取 now() 并剥掉时区，避免默认渲染出
            时区段；其余构造参数原样透传父类 DateInput。
        """
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
