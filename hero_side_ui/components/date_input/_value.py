"""DateInput 的日期时间值原语（零 Qt 依赖）。

对齐 HeroUI 背后的 @internationalized/date：在 Calendar 已有的 CalendarDate
（纯日期）之上补出时间与时区维度，形成本组件统一的值对象 DateTimeValue。

三种值形态用 has_time / timezone 两个维度区分：
  - CalendarDate 语义：has_time=False
  - CalendarDateTime 语义：has_time=True, timezone=None
  - ZonedDateTime 语义：has_time=True, timezone="America/Los_Angeles"
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

import icu

from ..calendar._date import CalendarDate, _fresh_calendar, _locale_for


@dataclass(frozen=True)
class DateTimeValue:
    """不可变的日期(+时间(+时区))值。

    所有修改都返回新实例，便于当 dict key、也便于状态层无副作用推演。

    :param year: 年（按 identifier 所指历法的纪年）
    :param month: 月，1-based
    :param day: 日
    :param hour: 时，24 小时制 0~23
    :param minute: 分
    :param second: 秒
    :param identifier: ICU 历法标识（gregorian/buddhist/indian/japanese/...）
    :param timezone: IANA 时区名；None 表示不带时区
    :param has_time: 是否携带时间部分
    """

    year: int
    month: int
    day: int
    hour: int = 0
    minute: int = 0
    second: int = 0
    identifier: str = "gregorian"
    timezone: Optional[str] = None
    has_time: bool = False

    # ---- 与 CalendarDate 互转 ------------------------------------------

    @property
    def date(self) -> CalendarDate:
        """丢弃时间部分，取纯日期视图（复用 Calendar 的日期运算能力）。"""
        return CalendarDate(self.year, self.month, self.day, self.identifier)

    @staticmethod
    def from_date(
        date: CalendarDate,
        *,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        timezone: Optional[str] = None,
        has_time: bool = False,
    ) -> "DateTimeValue":
        return DateTimeValue(
            year=date.year,
            month=date.month,
            day=date.day,
            hour=hour,
            minute=minute,
            second=second,
            identifier=date.identifier,
            timezone=timezone,
            has_time=has_time,
        )

    def with_date(self, date: CalendarDate) -> "DateTimeValue":
        """保留时间/时区，替换日期部分。"""
        return replace(self, year=date.year, month=date.month, day=date.day)

    def with_fields(self, **kwargs) -> "DateTimeValue":
        """替换任意字段并返回新实例。

        溢出的日按目标月实际天数**截断**而非进位（1/31 改成 2 月 → 2/29），
        与 react-aria 段编辑的约束语义一致；ICU lenient 模式会滚到 3/2，不可用。
        """
        merged = replace(self, **kwargs)
        max_day = CalendarDate(
            merged.year, merged.month, 1, merged.identifier
        ).days_in_month
        if merged.day > max_day:
            merged = replace(merged, day=max_day)
        return merged

    # ---- 历法转换 ------------------------------------------------------

    def to_calendar(self, identifier: str) -> "DateTimeValue":
        """转换到另一历法，保持指向同一时刻（如公历 → 印度历）。"""
        if identifier == self.identifier:
            return self
        src = _fresh_calendar(self.identifier)
        src.clear()
        src.set(self.year, self.month - 1, self.day, self.hour, self.minute, self.second)
        dst = _fresh_calendar(identifier)
        dst.setTime(src.getTime())
        return replace(
            self,
            year=dst.get(icu.Calendar.YEAR),
            month=dst.get(icu.Calendar.MONTH) + 1,
            day=dst.get(icu.Calendar.DATE),
            identifier=identifier,
        )

    # ---- 比较 ----------------------------------------------------------

    def _ordinal(self) -> tuple:
        """跨历法可比的排序键：先归一到绝对时刻，再带上时间部分。"""
        return (self.date._ordinal(), self.hour, self.minute, self.second)

    def __lt__(self, other: "DateTimeValue") -> bool:
        return self._ordinal() < other._ordinal()

    def __le__(self, other: "DateTimeValue") -> bool:
        return self._ordinal() <= other._ordinal()

    def __gt__(self, other: "DateTimeValue") -> bool:
        return self._ordinal() > other._ordinal()

    def __ge__(self, other: "DateTimeValue") -> bool:
        return self._ordinal() >= other._ordinal()

    # ---- 展示 ----------------------------------------------------------

    def format(self, skeleton: str = "yMd", locale: str = "en_US") -> str:
        """按 ICU skeleton 格式化（供 demo 展示"已选日期"用）。"""
        loc = _locale_for_locale(locale, self.identifier)
        gen = icu.DateTimePatternGenerator.createInstance(loc)
        fmt = icu.SimpleDateFormat(gen.getBestPattern(skeleton), loc)
        cal = _fresh_calendar(self.identifier)
        if self.timezone:
            tz = icu.TimeZone.createTimeZone(self.timezone)
            cal.setTimeZone(tz)
            fmt.setTimeZone(tz)
        cal.clear()
        cal.set(self.year, self.month - 1, self.day, self.hour, self.minute, self.second)
        return str(fmt.format(cal.getTime()))


def _locale_for_locale(locale: str, identifier: str) -> icu.Locale:
    """把 locale 字符串与历法标识合成 ICU Locale。"""
    base = locale.replace("-", "_")
    if "@" in base:
        return icu.Locale.createFromName(base)
    if identifier and identifier != "gregorian":
        return icu.Locale.createFromName(f"{base}@calendar={identifier}")
    return icu.Locale.createFromName(base)


def clamp_value(
    value: DateTimeValue,
    min_value: Optional[DateTimeValue],
    max_value: Optional[DateTimeValue],
) -> DateTimeValue:
    """把值夹到 [min, max] 区间内。"""
    if min_value is not None and value < min_value:
        return min_value
    if max_value is not None and value > max_value:
        return max_value
    return value


# ---- 构造入口（对齐 @internationalized/date 的解析函数）-----------------


def parse_date(text: str, identifier: str = "gregorian") -> DateTimeValue:
    """解析 "2024-04-04" 为纯日期值。"""
    y, m, d = (int(p) for p in text.split("-"))
    return DateTimeValue(y, m, d, identifier=identifier, has_time=False)


def parse_datetime(text: str, identifier: str = "gregorian") -> DateTimeValue:
    """解析 "2024-04-04T18:45:22" 为不带时区的日期时间值。"""
    date_part, _, time_part = text.partition("T")
    y, m, d = (int(p) for p in date_part.split("-"))
    hh, mm, ss = _parse_time_part(time_part)
    return DateTimeValue(y, m, d, hh, mm, ss, identifier=identifier, has_time=True)


def parse_zoned_datetime(text: str, identifier: str = "gregorian") -> DateTimeValue:
    """解析 "2022-11-07T00:45[America/Los_Angeles]" 为带时区的值。"""
    tz = None
    if "[" in text:
        text, _, tail = text.partition("[")
        tz = tail.rstrip("]")
    value = parse_datetime(text, identifier)
    return replace(value, timezone=tz)


def parse_absolute_to_local(text: str, identifier: str = "gregorian") -> DateTimeValue:
    """解析 UTC 时刻 "2021-04-07T18:45:22Z" 并转换到本机时区。"""
    body = text.rstrip("Z")
    date_part, _, time_part = body.partition("T")
    y, m, d = (int(p) for p in date_part.split("-"))
    hh, mm, ss = _parse_time_part(time_part)

    utc = icu.Calendar.createInstance(
        icu.TimeZone.getGMT(), _locale_for(identifier)
    )
    utc.clear()
    utc.set(y, m - 1, d, hh, mm, ss)

    local_tz = icu.TimeZone.createDefault()
    local = _fresh_calendar(identifier)
    local.setTimeZone(local_tz)
    local.setTime(utc.getTime())
    return DateTimeValue(
        year=local.get(icu.Calendar.YEAR),
        month=local.get(icu.Calendar.MONTH) + 1,
        day=local.get(icu.Calendar.DATE),
        hour=local.get(icu.Calendar.HOUR_OF_DAY),
        minute=local.get(icu.Calendar.MINUTE),
        second=local.get(icu.Calendar.SECOND),
        identifier=identifier,
        timezone=str(local_tz.getID()),
        has_time=True,
    )


def now(timezone: Optional[str] = None, identifier: str = "gregorian") -> DateTimeValue:
    """当前时刻（带时间，可指定时区）。"""
    tz = (
        icu.TimeZone.createTimeZone(timezone)
        if timezone
        else icu.TimeZone.createDefault()
    )
    cal = _fresh_calendar(identifier)
    cal.setTimeZone(tz)
    cal.setTime(icu.Calendar.getNow())
    return DateTimeValue(
        year=cal.get(icu.Calendar.YEAR),
        month=cal.get(icu.Calendar.MONTH) + 1,
        day=cal.get(icu.Calendar.DATE),
        hour=cal.get(icu.Calendar.HOUR_OF_DAY),
        minute=cal.get(icu.Calendar.MINUTE),
        second=cal.get(icu.Calendar.SECOND),
        identifier=identifier,
        timezone=str(tz.getID()),
        has_time=True,
    )


def today(identifier: str = "gregorian") -> DateTimeValue:
    """今天（纯日期）。"""
    return DateTimeValue.from_date(CalendarDate.today(identifier))


def _parse_time_part(time_part: str) -> tuple:
    """把 "18:45:22" / "00:45" / "" 解析成 (hour, minute, second)。"""
    if not time_part:
        return 0, 0, 0
    # 去掉可能的 UTC 偏移后缀（如 "00:45-08:00" 中的 -08:00）
    for sign in ("+", "-"):
        idx = time_part.find(sign, 1)
        if idx > 0:
            time_part = time_part[:idx]
            break
    bits = [int(float(p)) for p in time_part.split(":")]
    while len(bits) < 3:
        bits.append(0)
    return bits[0], bits[1], bits[2]


__all__ = [
    "DateTimeValue",
    "clamp_value",
    "now",
    "parse_absolute_to_local",
    "parse_date",
    "parse_datetime",
    "parse_zoned_datetime",
    "today",
]
