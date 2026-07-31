"""Calendar 组件的日期原语层（零 Qt 依赖）。

对齐 HeroUI 背后的 @internationalized/date：用 PyICU 提供多历法支持，
对外暴露一个不可变、可哈希、可比较的 CalendarDate，屏蔽 ICU 的
0-based month / 1-based weekday 等易错细节。

命名约定：
  - month 对外 1-based（1=一月），内部转 ICU 的 0-based。
  - weekday 采用 ICU 原生 1-based（SUN=1 .. SAT=7），与 first_day_of_week 一致。
  - identifier 为 ICU calendar keyword（gregorian/buddhist/japanese/...）。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import icu

# ICU 周字段常量（1-based，周日=1）
SUN, MON, TUE, WED, THU, FRI, SAT = 1, 2, 3, 4, 5, 6, 7

# firstDayOfWeek 字符串 → ICU weekday 常量
_FIRST_DAY_MAP = {
    "sun": SUN, "mon": MON, "tue": TUE, "wed": WED,
    "thu": THU, "fri": FRI, "sat": SAT,
}


@lru_cache(maxsize=32)
def _locale_for(identifier: str) -> icu.Locale:
    """缓存历法对应的 Locale（Calendar 本身很轻，每次新建即可）。"""
    return icu.Locale.createFromName(f"en_US@calendar={identifier}")


def _fresh_calendar(identifier: str) -> icu.Calendar:
    """新建一个干净的 Calendar 实例用于本次运算。

    PyICU 未暴露 Calendar.clone，故不缓存实例、每次 createInstance，
    避免跨调用共享导致的字段污染。
    """
    cal = icu.Calendar.createInstance(_locale_for(identifier))
    cal.setLenient(True)
    return cal


@dataclass(frozen=True)
class CalendarDate:
    """不可变的日历日期（年/月/日 + 历法标识）。

    所有算术都返回新实例，绝不原地修改，便于当作 dict key / set 成员，
    也便于逻辑层无副作用地推演状态。
    """

    year: int
    month: int  # 1-based
    day: int
    identifier: str = "gregorian"

    # ---- 构造 / 转换 ---------------------------------------------------

    @staticmethod
    def today(identifier: str = "gregorian") -> "CalendarDate":
        """返回该历法下的今天。"""
        cal = _fresh_calendar(identifier)
        cal.setTime(icu.Calendar.getNow())
        return CalendarDate._from_icu(cal, identifier)

    @staticmethod
    def _from_icu(cal: icu.Calendar, identifier: str) -> "CalendarDate":
        return CalendarDate(
            year=cal.get(icu.Calendar.YEAR),
            month=cal.get(icu.Calendar.MONTH) + 1,
            day=cal.get(icu.Calendar.DATE),
            identifier=identifier,
        )

    def _to_icu(self) -> icu.Calendar:
        """把本日期写进一个新的 ICU Calendar（时间归零到当天 0 点）。"""
        cal = _fresh_calendar(self.identifier)
        cal.clear()
        cal.set(self.year, self.month - 1, self.day)
        return cal

    # ---- 派生字段 -----------------------------------------------------

    @property
    def weekday(self) -> int:
        """ICU 1-based 星期（周日=1 .. 周六=7）。"""
        return self._to_icu().get(icu.Calendar.DAY_OF_WEEK)

    @property
    def days_in_month(self) -> int:
        """当月天数。"""
        return self._to_icu().getActualMaximum(icu.Calendar.DATE)

    # ---- 算术 ---------------------------------------------------------

    def add(self, *, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0) -> "CalendarDate":
        """按 ICU add 规则做日期加减（月末进位安全，如 1/31 + 1 月 = 2/28）。"""
        cal = self._to_icu()
        if years:
            cal.add(icu.Calendar.YEAR, years)
        if months:
            cal.add(icu.Calendar.MONTH, months)
        if weeks:
            cal.add(icu.Calendar.DATE, weeks * 7)
        if days:
            cal.add(icu.Calendar.DATE, days)
        return CalendarDate._from_icu(cal, self.identifier)

    def with_fields(self, *, year: Optional[int] = None, month: Optional[int] = None,
                    day: Optional[int] = None) -> "CalendarDate":
        """返回替换了指定字段的新日期（用于 picker 直接设年/月）。"""
        cal = _fresh_calendar(self.identifier)
        cal.clear()
        cal.set(
            self.year if year is None else year,
            (self.month if month is None else month) - 1,
            self.day if day is None else day,
        )
        return CalendarDate._from_icu(cal, self.identifier)

    def first_of_month(self) -> "CalendarDate":
        return CalendarDate(self.year, self.month, 1, self.identifier)

    def last_of_month(self) -> "CalendarDate":
        return CalendarDate(self.year, self.month, self.days_in_month, self.identifier)

    # ---- 比较（同历法按时间轴，跨历法按绝对时刻）-----------------------

    def _ordinal(self) -> float:
        """归一到 ICU 毫秒时刻，用于跨历法比较。"""
        return self._to_icu().getTime()

    def __lt__(self, other: "CalendarDate") -> bool:
        return self._ordinal() < other._ordinal()

    def __le__(self, other: "CalendarDate") -> bool:
        return self._ordinal() <= other._ordinal()

    def __gt__(self, other: "CalendarDate") -> bool:
        return self._ordinal() > other._ordinal()

    def __ge__(self, other: "CalendarDate") -> bool:
        return self._ordinal() >= other._ordinal()

    def is_same_day(self, other: Optional["CalendarDate"]) -> bool:
        if other is None:
            return False
        return (self.year, self.month, self.day) == (other.year, other.month, other.day)

    def is_same_month(self, other: Optional["CalendarDate"]) -> bool:
        if other is None:
            return False
        return (self.year, self.month) == (other.year, other.month)


def normalize_first_day_of_week(value: Optional[str]) -> int:
    """把 'sun'/'mon'/... 归一为 ICU weekday 常量；None → 周日(SUN)。"""
    if value is None:
        return SUN
    key = value.strip().lower()
    if key not in _FIRST_DAY_MAP:
        raise ValueError(f"invalid first_day_of_week: {value!r}")
    return _FIRST_DAY_MAP[key]


def weeks_in_month(date: CalendarDate, first_day_of_week: int) -> int:
    """给定月份在指定周起点下需要几行（4~6）。"""
    first = date.first_of_month()
    lead = (first.weekday - first_day_of_week) % 7
    total = lead + date.days_in_month
    return -(-total // 7)  # 向上取整


def clamp_date(date: CalendarDate, min_value: Optional[CalendarDate],
               max_value: Optional[CalendarDate]) -> CalendarDate:
    """把日期夹到 [min, max] 区间内。"""
    if min_value is not None and date < min_value:
        return min_value
    if max_value is not None and date > max_value:
        return max_value
    return date


# ---- 本地化文本（星期名 / 月份标题 / 月名 / 年号）---------------------

_WEEKDAY_WIDTH = {
    "narrow": icu.DateFormatSymbols.NARROW,
    "short": icu.DateFormatSymbols.ABBREVIATED,
    "long": icu.DateFormatSymbols.WIDE,
}


@lru_cache(maxsize=64)
def _symbols(identifier: str) -> icu.DateFormatSymbols:
    return icu.DateFormatSymbols(_locale_for(identifier))


def weekday_names(first_day_of_week: int, style: str = "narrow",
                  identifier: str = "gregorian") -> list:
    """按周起点排好序的 7 个星期名（style: narrow/short/long）。"""
    sym = _symbols(identifier)
    width = _WEEKDAY_WIDTH.get(style, icu.DateFormatSymbols.NARROW)
    # ICU 数组 1-based：index 0 为空，1=周日 .. 7=周六
    raw = list(sym.getWeekdays(icu.DateFormatSymbols.FORMAT, width))
    return [raw[((first_day_of_week - 1 + i) % 7) + 1] for i in range(7)]


@lru_cache(maxsize=256)
def month_title(year: int, month: int, identifier: str = "gregorian") -> str:
    """月份标题，如 'July 2026'（随历法/locale 本地化）。"""
    cal = _fresh_calendar(identifier)
    cal.clear()
    cal.set(year, month - 1, 1)
    fmt = icu.SimpleDateFormat("MMMM y", _locale_for(identifier))
    fmt.setCalendar(cal)
    return str(fmt.format(cal.getTime()))


def month_name(month: int, identifier: str = "gregorian") -> str:
    """单独的月名，如 'July'（用于月份选择器）。"""
    sym = _symbols(identifier)
    return list(sym.getMonths())[month - 1]


def months_in_year(identifier: str = "gregorian") -> list:
    """当前历法一年的 12 个月名（用于月份选择器列）。"""
    return list(_symbols(identifier).getMonths())[:12]


def year_range(min_value: "CalendarDate", max_value: "CalendarDate") -> list:
    """min~max 之间的年份列表（含端点，用于年份选择器列）。"""
    return list(range(min_value.year, max_value.year + 1))

