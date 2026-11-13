"""Calendar 日期原语层（零 Qt 依赖）：不可变可哈希的 CalendarDate。

基于 PyICU 多历法；month 对外 1-based，weekday 沿用 ICU 1-based（SUN=1）。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import icu

# ICU 周字段常量（1-based，周日=1）
SUN, MON, TUE, WED, THU, FRI, SAT = 1, 2, 3, 4, 5, 6, 7

# firstDayOfWeek 字符串 → ICU weekday 常量
_FIRST_DAY_MAP = {
    "sun": SUN,
    "mon": MON,
    "tue": TUE,
    "wed": WED,
    "thu": THU,
    "fri": FRI,
    "sat": SAT,
}


@lru_cache(maxsize=32)
def _locale_for(identifier: str) -> icu.Locale:
    """缓存历法对应的 Locale。

    Args:
        identifier: ICU 历法标识，如 gregorian。

    Returns:
        en_US@calendar=<identifier> 的 icu.Locale；Calendar 很轻故不缓存实例。
    """
    return icu.Locale.createFromName(f"en_US@calendar={identifier}")


def _fresh_calendar(identifier: str) -> icu.Calendar:
    """新建干净的 ICU Calendar 实例。

    Args:
        identifier: ICU 历法标识。

    Returns:
        lenient 模式的新 Calendar；PyICU 无 clone，不缓存防跨调用污染。
    """
    cal = icu.Calendar.createInstance(_locale_for(identifier))
    cal.setLenient(True)
    return cal


@dataclass(frozen=True)
class CalendarDate:
    """不可变日历日期：所有算术返回新实例，可当 dict key。"""

    year: int
    month: int  # 1-based
    day: int
    identifier: str = "gregorian"

    # ---- 构造 / 转换 ---------------------------------------------------

    @staticmethod
    def today(identifier: str = "gregorian") -> CalendarDate:
        """返回该历法下的今天。

        Args:
            identifier: ICU 历法标识。

        Returns:
            当前系统时间对应的 CalendarDate。
        """
        cal = _fresh_calendar(identifier)
        cal.setTime(icu.Calendar.getNow())
        return CalendarDate._from_icu(cal, identifier)

    @staticmethod
    def _from_icu(cal: icu.Calendar, identifier: str) -> CalendarDate:
        """从 ICU Calendar 读出年月日构造不可变日期。

        Args:
            cal: 已设好时间的 ICU Calendar。
            identifier: 历法标识，随实例保留。

        Returns:
            month 为 1-based 的 CalendarDate。
        """
        return CalendarDate(
            year=cal.get(icu.Calendar.YEAR),
            month=cal.get(icu.Calendar.MONTH) + 1,
            day=cal.get(icu.Calendar.DATE),
            identifier=identifier,
        )

    def _to_icu(self) -> icu.Calendar:
        """把本日期写进一个新的 ICU Calendar。

        Returns:
            时间归零到当天 0 点的新 Calendar；month 对外 1-based，
            写回 ICU 时需减 1。
        """
        cal = _fresh_calendar(self.identifier)
        cal.clear()
        cal.set(self.year, self.month - 1, self.day)
        return cal

    # ---- 派生字段 -----------------------------------------------------

    @property
    def weekday(self) -> int:
        """ICU 1-based 星期。

        Returns:
            周日=1 .. 周六=7。
        """
        return self._to_icu().get(icu.Calendar.DAY_OF_WEEK)

    @property
    def days_in_month(self) -> int:
        """当月天数。

        Returns:
            当前历法下该月的实际最大日数。
        """
        return self._to_icu().getActualMaximum(icu.Calendar.DATE)

    # ---- 算术 ---------------------------------------------------------

    def add(
        self, *, years: int = 0, months: int = 0, weeks: int = 0, days: int = 0
    ) -> CalendarDate:
        """按 ICU add 规则做日期加减。

        Args:
            years: 年偏移。
            months: 月偏移（月末进位安全，如 1/31 + 1 月 = 2/28）。
            weeks: 周偏移，内部折算成天。
            days: 天偏移。

        Returns:
            新的 CalendarDate，原实例不变。
        """
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

    def with_fields(
        self, *, year: int | None = None, month: int | None = None, day: int | None = None
    ) -> CalendarDate:
        """返回替换了指定字段的新日期（用于 picker 直接设年/月）。

        Args:
            year: 新年；None 保持。
            month: 新月（1-based）；None 保持。
            day: 新日；None 保持。

        Returns:
            新的 CalendarDate；跨月由 ICU lenient 归一化。
        """
        cal = _fresh_calendar(self.identifier)
        cal.clear()
        cal.set(
            self.year if year is None else year,
            (self.month if month is None else month) - 1,
            self.day if day is None else day,
        )
        return CalendarDate._from_icu(cal, self.identifier)

    def first_of_month(self) -> CalendarDate:
        """返回当月 1 号。

        Returns:
            同年月、day=1 的新实例。
        """
        return CalendarDate(self.year, self.month, 1, self.identifier)

    def last_of_month(self) -> CalendarDate:
        """返回当月最后一天。

        Returns:
            同年月、day=days_in_month 的新实例。
        """
        return CalendarDate(self.year, self.month, self.days_in_month, self.identifier)

    # ---- 比较（同历法按时间轴，跨历法按绝对时刻）-----------------------

    def _ordinal(self) -> float:
        """归一到 ICU 毫秒时刻，用于跨历法比较。

        Returns:
            该日期 0 点对应的 ICU 毫秒时间戳。
        """
        return self._to_icu().getTime()

    def __lt__(self, other: CalendarDate) -> bool:
        """小于比较（按绝对时刻）。"""
        return self._ordinal() < other._ordinal()

    def __le__(self, other: CalendarDate) -> bool:
        """小于等于比较（按绝对时刻）。"""
        return self._ordinal() <= other._ordinal()

    def __gt__(self, other: CalendarDate) -> bool:
        """大于比较（按绝对时刻）。"""
        return self._ordinal() > other._ordinal()

    def __ge__(self, other: CalendarDate) -> bool:
        """大于等于比较（按绝对时刻）。"""
        return self._ordinal() >= other._ordinal()

    def is_same_day(self, other: CalendarDate | None) -> bool:
        """判断是否为同一天（按年月日字段，不比较历法）。

        Args:
            other: 待比较的日期；None 恒 False。

        Returns:
            (year, month, day) 完全相同为 True。
        """
        if other is None:
            return False
        return (self.year, self.month, self.day) == (other.year, other.month, other.day)

    def is_same_month(self, other: CalendarDate | None) -> bool:
        """判断是否为同一月（按年月字段）。

        Args:
            other: 待比较的日期；None 恒 False。

        Returns:
            (year, month) 相同为 True。
        """
        if other is None:
            return False
        return (self.year, self.month) == (other.year, other.month)


def normalize_first_day_of_week(value: str | None) -> int:
    """把周起点字符串归一为 ICU weekday 常量。

    Args:
        value: sun / mon / ... / sat；None 表示默认周日。

    Returns:
        对应 ICU 1-based weekday 常量。

    Raises:
        ValueError: value 不是合法周起点时抛出。
    """
    if value is None:
        return SUN
    key = value.strip().lower()
    if key not in _FIRST_DAY_MAP:
        raise ValueError(f"invalid first_day_of_week: {value!r}")
    return _FIRST_DAY_MAP[key]


def weeks_in_month(date: CalendarDate, first_day_of_week: int) -> int:
    """给定月份在指定周起点下需要几行。

    Args:
        date: 当月任一天。
        first_day_of_week: 周起点（ICU weekday 常量）。

    Returns:
        4~6 的周行数（向上取整）。
    """
    first = date.first_of_month()
    lead = (first.weekday - first_day_of_week) % 7
    total = lead + date.days_in_month
    return -(-total // 7)  # 向上取整


def clamp_date(
    date: CalendarDate, min_value: CalendarDate | None, max_value: CalendarDate | None
) -> CalendarDate:
    """把日期夹到 [min, max] 区间内。

    Args:
        date: 待钳制日期。
        min_value: 下界；None 表示不限。
        max_value: 上界；None 表示不限。

    Returns:
        越界时返回对应边界，否则原样返回。
    """
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
    """缓存历法对应的本地化日期符号表。

    Args:
        identifier: ICU 历法标识。

    Returns:
        该 locale 的 icu.DateFormatSymbols。
    """
    return icu.DateFormatSymbols(_locale_for(identifier))


def weekday_names(
    first_day_of_week: int, style: str = "narrow", identifier: str = "gregorian"
) -> list:
    """按周起点排好序的 7 个星期名。

    Args:
        first_day_of_week: 周起点（ICU weekday 常量）。
        style: narrow / short / long 三种宽度。
        identifier: ICU 历法标识。

    Returns:
        7 个本地化星期名；ICU 数组 1-based，index 0 为空。
    """
    sym = _symbols(identifier)
    width = _WEEKDAY_WIDTH.get(style, icu.DateFormatSymbols.NARROW)
    # ICU 数组 1-based：index 0 为空，1=周日 .. 7=周六
    raw = list(sym.getWeekdays(icu.DateFormatSymbols.FORMAT, width))
    return [raw[((first_day_of_week - 1 + i) % 7) + 1] for i in range(7)]


@lru_cache(maxsize=256)
def month_title(year: int, month: int, identifier: str = "gregorian") -> str:
    """本地化的月份标题。

    Args:
        year: 年。
        month: 月（1-based）。
        identifier: ICU 历法标识。

    Returns:
        如 'July 2026' 的本地化字符串。
    """
    cal = _fresh_calendar(identifier)
    cal.clear()
    cal.set(year, month - 1, 1)
    fmt = icu.SimpleDateFormat("MMMM y", _locale_for(identifier))
    fmt.setCalendar(cal)
    return str(fmt.format(cal.getTime()))


def month_name(month: int, identifier: str = "gregorian") -> str:
    """单独的月名。

    Args:
        month: 月（1-based）。
        identifier: ICU 历法标识。

    Returns:
        如 'July'，用于月份选择器列。
    """
    sym = _symbols(identifier)
    return list(sym.getMonths())[month - 1]


def months_in_year(identifier: str = "gregorian") -> list:
    """当前历法一年的月名列表。

    Args:
        identifier: ICU 历法标识。

    Returns:
        前 12 个月名，用于月份选择器列。
    """
    return list(_symbols(identifier).getMonths())[:12]


def year_range(min_value: CalendarDate, max_value: CalendarDate) -> list:
    """可选年份列表。

    Args:
        min_value: 下界日期。
        max_value: 上界日期。

    Returns:
        含两端点的年份列表，用于年份选择器列。
    """
    return list(range(min_value.year, max_value.year + 1))
