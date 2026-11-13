"""日期家族共享的纯模型（无 Qt 依赖）。

CalendarDate 与日历计算、DateTimeValue 及解析函数、分段模式、DateFieldState
段编辑状态机，供 Calendar、DateInput、TimeInput、DatePicker 与范围组件共用。
控件侧的外观与交互仍由各组件持有。
"""

from .calendar_date import (
    FRI,
    MON,
    SAT,
    SUN,
    THU,
    TUE,
    WED,
    CalendarDate,
    clamp_date,
    month_name,
    month_title,
    months_in_year,
    normalize_first_day_of_week,
    weekday_names,
    weeks_in_month,
    year_range,
)
from .field_state import DateFieldState
from .pattern import (
    EDITABLE_TYPES,
    TIME_GRANULARITIES,
    VALID_GRANULARITIES,
    SegmentSpec,
    build_pattern,
    build_segments,
    parse_pattern,
)
from .value import (
    DateTimeValue,
    clamp_value,
    now,
    parse_absolute_to_local,
    parse_date,
    parse_datetime,
    parse_zoned_datetime,
    today,
)

__all__ = [
    "EDITABLE_TYPES",
    "FRI",
    "MON",
    "SAT",
    "SUN",
    "THU",
    "TIME_GRANULARITIES",
    "TUE",
    "VALID_GRANULARITIES",
    "WED",
    "CalendarDate",
    "DateFieldState",
    "DateTimeValue",
    "SegmentSpec",
    "build_pattern",
    "build_segments",
    "clamp_date",
    "clamp_value",
    "month_name",
    "month_title",
    "months_in_year",
    "normalize_first_day_of_week",
    "now",
    "parse_absolute_to_local",
    "parse_date",
    "parse_datetime",
    "parse_pattern",
    "parse_zoned_datetime",
    "today",
    "weekday_names",
    "weeks_in_month",
    "year_range",
]
