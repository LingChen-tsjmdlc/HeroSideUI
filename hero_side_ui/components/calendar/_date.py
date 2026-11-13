"""兼容入口：旧路径 calendar._date。

新代码请从 hero_side_ui.components.calendar 导入 CalendarDate，
日历计算函数位于 hero_side_ui._shared.dates。
"""

from ..._shared.dates import (
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

__all__ = [
    "FRI",
    "MON",
    "SAT",
    "SUN",
    "THU",
    "TUE",
    "WED",
    "CalendarDate",
    "clamp_date",
    "month_name",
    "month_title",
    "months_in_year",
    "normalize_first_day_of_week",
    "weekday_names",
    "weeks_in_month",
    "year_range",
]
