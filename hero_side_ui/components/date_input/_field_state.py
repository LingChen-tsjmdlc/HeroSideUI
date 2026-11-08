"""段编辑状态机：复刻 react-stately 的 useDateFieldState（零 Qt 依赖）。"""

from __future__ import annotations

from functools import lru_cache

import icu

from ..calendar._date import CalendarDate, _fresh_calendar
from ._pattern import SegmentSpec, build_segments
from ._value import DateTimeValue, _locale_for_locale

# 各段的取值范围上界（year 上界由 max_value 决定，month/day 依赖具体年月）
_HOUR12_MIN = 1
_HOUR12_MAX = 12
_HOUR24_MIN = 0
_HOUR24_MAX = 23

# 占位显示文本：位数不足时重复填充
_PLACEHOLDER_CHAR = {
    "year": "y",
    "month": "m",
    "day": "d",
    "hour": "h",
    "minute": "m",
    "second": "s",
}


@lru_cache(maxsize=64)
def _era_names(locale: str, identifier: str) -> tuple:
    """取该历法的纪元名列表。

    Args:
        locale: ICU locale 字符串。
        identifier: ICU 历法标识。

    Returns:
        本地化纪元名的元组；结果按参数 lru_cache 缓存。

    Note:
        必须用 DateFormatSymbols 两参重载；单参会无视 locale 的
        @calendar= 关键字导致印度历错拿公历纪元。
    """
    loc = _locale_for_locale(locale, identifier)
    try:
        return tuple(str(e) for e in icu.DateFormatSymbols(loc, identifier).getEras())
    except Exception:
        return tuple(str(e) for e in icu.DateFormatSymbols(loc).getEras())


class DateFieldState:
    """DateInput 的段编辑状态机。

    Args:
        value: 受控初始值；None 表示全占位。
        placeholder_value: 占位时各段增减的起点值。
        granularity: day/hour/minute/second。
        hour_cycle: 12 或 24；None 跟随 locale。
        locale: ICU locale 字符串。
        identifier: ICU 历法标识。
        min_value: 值域下界，段提交时 clamp。
        max_value: 值域上界。
        hide_time_zone: 隐藏时区段。
        should_force_leading_zeros: 数字段补前导零。
        include_date: False 时为纯时间状态机（TimeInput）。
    """

    def __init__(
        self,
        *,
        value: DateTimeValue | None = None,
        placeholder_value: DateTimeValue | None = None,
        granularity: str = "day",
        hour_cycle: int | None = None,
        locale: str = "en_US",
        identifier: str = "gregorian",
        min_value: DateTimeValue | None = None,
        max_value: DateTimeValue | None = None,
        hide_time_zone: bool = False,
        should_force_leading_zeros: bool = True,
        include_date: bool = True,
    ):
        """创建段编辑状态机。

        Args:
            value: 受控初始值；None 表示全占位。
            placeholder_value: 占位时各段增减的起点值；None 用今天。
            granularity: day / hour / minute / second。
            hour_cycle: 12 或 24；None 跟随 locale。
            locale: ICU locale 字符串。
            identifier: ICU 历法标识。
            min_value: 值域下界，段提交时 clamp。
            max_value: 值域上界。
            hide_time_zone: 隐藏时区段。
            should_force_leading_zeros: 数字段补前导零。
            include_date: False 时为纯时间状态机（TimeInput）。

        Note:
            时区取自 value 或 placeholder_value，决定 timeZone 段是否出现。
        """
        self._granularity = granularity
        self._hour_cycle = hour_cycle
        self._locale = locale
        self._identifier = identifier
        self._min_value = min_value
        self._max_value = max_value
        self._hide_time_zone = hide_time_zone
        self._force_zeros = should_force_leading_zeros
        self._include_date = include_date

        # 占位起点：优先 placeholder_value，其次今天
        base = placeholder_value or DateTimeValue.from_date(CalendarDate.today(identifier))
        self._placeholder = base.to_calendar(identifier)

        # 时区取自值或占位值（决定是否出现 timeZone 段）
        self._timezone = None
        if value is not None and value.timezone:
            self._timezone = value.timezone
        elif placeholder_value is not None and placeholder_value.timezone:
            self._timezone = placeholder_value.timezone

        self._specs: list[SegmentSpec] = build_segments(
            locale=locale,
            identifier=identifier,
            granularity=granularity,
            hour_cycle=hour_cycle,
            hide_time_zone=hide_time_zone,
            has_timezone=self._timezone is not None,
            include_date=include_date,
        )

        # 段值表：type → int；缺席即占位态
        self._values: dict[str, int] = {}
        if value is not None:
            self.set_value(value)

    # ============================================================
    # 结构查询
    # ============================================================
    @property
    def specs(self) -> list[SegmentSpec]:
        """段结构描述列表。

        Returns:
            按显示顺序排列的 SegmentSpec 列表。
        """
        return self._specs

    @property
    def granularity(self) -> str:
        """时间粒度。

        Returns:
            day / hour / minute / second。
        """
        return self._granularity

    @property
    def include_date(self) -> bool:
        """是否含日期段。

        Returns:
            False 表示纯时间状态机（TimeInput 复用）。
        """
        return self._include_date

    @property
    def timezone(self) -> str | None:
        """当前时区标识。

        Returns:
            时区字符串；无时区段时为 None。
        """
        return self._timezone

    @property
    def editable_types(self) -> list[str]:
        """可编辑段类型列表。

        Returns:
            specs 中 is_editable 为 True 的 type 列表。
        """
        return [s.type for s in self._specs if s.is_editable]

    def is_placeholder(self, seg_type: str) -> bool:
        """该段是否仍是占位态。

        Args:
            seg_type: 段类型。

        Returns:
            未写入值时为 True；派生段（era / dayPeriod / timeZone）
            按依赖段判定，timeZone 恒不算占位。
        """
        if seg_type == "timeZone":
            return False
        if seg_type == "dayPeriod":
            return "hour" not in self._values and "dayPeriod" not in self._values
        if seg_type == "era":
            return "year" not in self._values and "era" not in self._values
        return seg_type not in self._values

    def has_any_input(self) -> bool:
        """是否至少填了一个段（用于 label 浮起判断）。

        Returns:
            段值表非空时为 True。
        """
        return bool(self._values)

    def is_complete(self) -> bool:
        """所有可编辑段是否都已填。

        Returns:
            era / dayPeriod / timeZone 有默认值不算必填，其余段全填才为 True。
        """
        return all(
            t in self._values
            for t in self.editable_types
            if t not in ("era", "dayPeriod", "timeZone")
        )

    # ============================================================
    # 值读写
    # ============================================================
    def value(self) -> DateTimeValue | None:
        """把当前段组合成值对象。

        Returns:
            段全填好时返回 DateTimeValue；否则 None（对齐 HeroUI 的 null 语义）。
        """
        if not self.is_complete():
            return None
        return self._compose()

    def set_value(self, value: DateTimeValue | None) -> None:
        """外部受控赋值：拆解成各段值。

        Args:
            value: 新值；None 清空全部段。

        Note:
            先按当前历法换算；时间相关段按 granularity 决定是否写入。
        """
        if value is None:
            self._values.clear()
            return
        v = value.to_calendar(self._identifier)
        self._values = {"year": v.year, "month": v.month, "day": v.day}
        if self._granularity != "day":
            self._values["hour"] = v.hour
            if self._granularity in ("minute", "second"):
                self._values["minute"] = v.minute
            if self._granularity == "second":
                self._values["second"] = v.second
        if v.timezone:
            self._timezone = v.timezone

    def clear(self) -> None:
        """清空全部段值，回到占位态。"""
        self._values.clear()

    def clear_segment(self, seg_type: str) -> None:
        """清空指定段。

        Args:
            seg_type: 段类型。
        """
        self._values.pop(seg_type, None)

    def _compose(self) -> DateTimeValue:
        """把当前段值合成 DateTimeValue（不做 clamp）。

        Returns:
            缺席段用占位值兜底的 DateTimeValue。
        """
        ph = self._placeholder
        hour = self._values.get("hour", ph.hour)
        return DateTimeValue(
            year=self._values.get("year", ph.year),
            month=self._values.get("month", ph.month),
            day=self._values.get("day", ph.day),
            hour=hour if self._granularity != "day" else 0,
            minute=self._values.get("minute", 0)
            if self._granularity in ("minute", "second")
            else 0,
            second=self._values.get("second", 0) if self._granularity == "second" else 0,
            identifier=self._identifier,
            timezone=self._timezone,
            has_time=self._granularity != "day",
        )

    # ============================================================
    # 段的显示文本
    # ============================================================
    def segment_text(self, seg_type: str, min_digits: int = 1) -> str:
        """段的显示文本；占位态返回 mm / dd / yyyy 之类的提示符。

        Args:
            seg_type: 段类型。
            min_digits: pattern 给出的最小位数。

        Returns:
            已填段返回按宽度补零的字符串；占位段返回重复的占位字符。
        """
        if seg_type == "timeZone":
            return self._timezone_text()
        if seg_type == "era":
            return self._era_text()
        if seg_type == "dayPeriod":
            return self._day_period_text()

        if self.is_placeholder(seg_type):
            width = self._display_width(seg_type, min_digits)
            return _PLACEHOLDER_CHAR.get(seg_type, "-") * width

        raw = self._values[seg_type]
        if seg_type == "hour" and self._is_hour12():
            raw = raw % 12 or 12
        width = self._display_width(seg_type, min_digits)
        if self._force_zeros or seg_type == "year":
            return str(raw).zfill(width)
        return str(raw)

    def _display_width(self, seg_type: str, min_digits: int) -> int:
        """取段显示宽度。

        Args:
            seg_type: 段类型。
            min_digits: pattern 给出的最小位数。

        Returns:
            年 4 位（带 era 历法按 pattern 位数）、其余至少 2 位。
        """
        if seg_type == "year":
            return min_digits if self._has_era_segment() else 4
        return max(2, min_digits)

    def _has_era_segment(self) -> bool:
        """当前段结构是否含 era 段。

        Returns:
            specs 中存在 type == era 时为 True。
        """
        return any(s.type == "era" for s in self._specs)

    def _timezone_text(self) -> str:
        """按时区与当前日期格式化时区名。

        Returns:
            ICU SimpleDateFormat("zzz") 的结果；无时区时返回空串。
        """
        if not self._timezone:
            return ""
        tz = icu.TimeZone.createTimeZone(self._timezone)
        cal = _fresh_calendar(self._identifier)
        cal.setTimeZone(tz)
        v = self._compose()
        cal.clear()
        cal.set(v.year, v.month - 1, v.day, v.hour, v.minute, v.second)
        fmt = icu.SimpleDateFormat("zzz", _locale_for_locale(self._locale, self._identifier))
        fmt.setTimeZone(tz)
        return str(fmt.format(cal.getTime()))

    def _era_text(self) -> str:
        """按当前年代值取本地化纪元名。

        Returns:
            对应纪元名；未填 era 段时按当前日期的 ERA 字段推断。
        """
        eras = _era_names(self._locale, self._identifier)
        idx = self._values.get("era")
        if idx is None:
            cal = self._compose().date._to_icu()
            idx = cal.get(icu.Calendar.ERA)
        return str(eras[idx]) if 0 <= idx < len(eras) else ""

    def _day_period_text(self) -> str:
        """取 AM / PM 本地化文本。

        Returns:
            dayPeriod 段值对应的 ampm 字符串；未填时按当前小时推断。
        """
        sym = icu.DateFormatSymbols(_locale_for_locale(self._locale, self._identifier))
        ampm = list(sym.getAmPmStrings())
        pm = self._values.get("dayPeriod")
        if pm is None:
            pm = 1 if self._values.get("hour", self._placeholder.hour) >= 12 else 0
        return str(
            ampm[1] if pm else ampm[0]
        )  # ============================================================

    # 编辑动作
    # ============================================================
    def _is_hour12(self) -> bool:
        """当前是否 12 小时制。

        Returns:
            specs 中含 dayPeriod 段即为 12 小时制。
        """
        return any(s.type == "dayPeriod" for s in self._specs)

    def segment_range(self, seg_type: str) -> tuple:
        """段的合法取值区间（闭区间）。

        Args:
            seg_type: 段类型。

        Returns:
            (lo, hi)；month / day 的上界依赖当前年月，基于已填段实时计算。
        """
        if seg_type == "year":
            lo = self._min_value.year if self._min_value else 1
            hi = self._max_value.year if self._max_value else 9999
            return lo, hi
        if seg_type == "month":
            return 1, 12
        if seg_type == "day":
            cur = self._compose()
            return 1, CalendarDate(cur.year, cur.month, 1, self._identifier).days_in_month
        if seg_type == "hour":
            if self._is_hour12():
                return _HOUR12_MIN, _HOUR12_MAX
            return _HOUR24_MIN, _HOUR24_MAX
        if seg_type in ("minute", "second"):
            return 0, 59
        if seg_type == "dayPeriod":
            return 0, 1
        if seg_type == "era":
            return 0, max(0, len(_era_names(self._locale, self._identifier)) - 1)
        return 0, 0

    def increment(self, seg_type: str, delta: int = 1) -> None:
        """上下键增减，越界回绕（对齐 react-aria 的 cycle 行为）。

        Args:
            seg_type: 段类型；timeZone 段直接忽略。
            delta: 增减步长，默认 +1。

        Note:
            段尚未显式写入时从占位值起步而非从 0，避免第一次按上键跳变。
        """
        if seg_type == "timeZone":
            return
        lo, hi = self.segment_range(seg_type)
        if seg_type in self._values:
            cur = self._values[seg_type]
            if seg_type == "hour" and self._is_hour12():
                cur = cur % 12 or 12
        else:
            # 该段还没被显式写过（含 dayPeriod/era 这类派生段）：
            # 从占位值起步，而不是从 0。
            cur = self._placeholder_segment_value(seg_type)
        span = hi - lo + 1
        new = lo + ((cur - lo + delta) % span)
        self._set_segment(seg_type, new)

    def _placeholder_segment_value(self, seg_type: str) -> int:
        """取段在未写入状态下的起步值。

        Args:
            seg_type: 段类型。

        Returns:
            占位值对应字段；dayPeriod 取实际生效小时推导，
            避免切 AM/PM 跳回占位那一半天。
        """
        ph = self._placeholder
        if seg_type == "year":
            return ph.year
        if seg_type == "month":
            return ph.month
        if seg_type == "day":
            return ph.day
        if seg_type == "hour":
            return (ph.hour % 12 or 12) if self._is_hour12() else ph.hour
        if seg_type == "minute":
            return ph.minute
        if seg_type == "second":
            return ph.second
        if seg_type == "dayPeriod":
            # 上/下午的当前值应取实际生效的小时（可能来自已填的 hour 段），
            # 不能只看占位值，否则切 AM/PM 会跳回占位那一半天。
            hour = self._values.get("hour", ph.hour)
            return 1 if hour >= 12 else 0
        return 0

    def _set_segment(self, seg_type: str, raw: int) -> None:
        """写入段值并做跨段一致性修正。

        Args:
            seg_type: 段类型。
            raw: 待写入的原始值。

        Note:
            12 小时制下输入 1~12 需按当前半天还原成 24 小时值；
            切 dayPeriod 时同步搬运 hour；改年/月后把 day 截到当月天数。
        """
        if seg_type == "hour" and self._is_hour12():
            # 12 小时制下用户输的是 1~12，需按当前半天归属还原成 24 小时值
            prev_hour = self._values.get("hour", self._placeholder.hour)
            pm = self._values.get("dayPeriod", 1 if prev_hour >= 12 else 0)
            raw = (raw % 12) + (12 if pm else 0)
        elif seg_type == "dayPeriod":
            # 切换半天时直接把已有 hour 搬到另一半天，避免二者不一致
            self._values[seg_type] = raw
            if "hour" in self._values:
                self._values["hour"] = (self._values["hour"] % 12) + (12 if raw else 0)
            return
        self._values[seg_type] = raw

        # 改年/月后，日可能超过当月天数 → 截断
        if seg_type in ("year", "month") and "day" in self._values:
            cur = self._compose()
            max_day = CalendarDate(cur.year, cur.month, 1, self._identifier).days_in_month
            if self._values["day"] > max_day:
                self._values["day"] = max_day

    def append_digit(self, seg_type: str, digit: int) -> bool:
        """逐位输入一个数字。

        Args:
            seg_type: 段类型。
            digit: 输入的数字字符。

        Returns:
            该段是否已输满（供自动跳段）。

        Note:
            中间态不做 clamp，否则两位年份会被 min_value 夹住输不进去。
        """
        if seg_type in ("timeZone", "era", "dayPeriod"):
            return False
        _lo, hi = self.segment_range(seg_type)
        width = 4 if seg_type == "year" else len(str(hi))

        typed = getattr(self, "_typing", {}).get(seg_type, "")
        typed = (typed + str(digit))[-width:]
        candidate = int(typed)

        # 溢出：本次输入无法接在已输部分后面，则重新从这一位开始
        if candidate > hi and len(typed) > 1:
            typed = str(digit)
            candidate = digit

        if not hasattr(self, "_typing"):
            self._typing = {}
        self._typing[seg_type] = typed

        self._set_segment(seg_type, max(candidate, 0))

        # 已输满位数，或再输一位必然溢出 → 认为该段完成
        done = len(typed) >= width or candidate * 10 > hi
        if done:
            self._typing.pop(seg_type, None)
            self.commit_segment(seg_type)
        return done

    def commit_segment(self, seg_type: str) -> None:
        """段编辑结束：把该段夹进自身物理范围（如月份 99 → 12）。

        Args:
            seg_type: 段类型；timeZone 段直接忽略。
        """
        if seg_type in ("timeZone",):
            return
        if hasattr(self, "_typing"):
            self._typing.pop(seg_type, None)
        if seg_type not in self._values:
            return
        lo, hi = self.segment_range(seg_type)
        cur = self._values[seg_type]
        if seg_type == "hour" and self._is_hour12():
            cur = cur % 12 or 12
        self._set_segment(seg_type, min(max(cur, lo), hi))

    def is_invalid(self) -> bool:
        """值是否越界。

        Returns:
            含日期段时按 DateTimeValue 全序比较 [min, max]；
            纯时间状态机只比较 (hour, minute, second) 三元组。
        """
        v = self.value()
        if v is None:
            return False
        if self._include_date:
            if self._min_value is not None and v < self._min_value:
                return True
            if self._max_value is not None and v > self._max_value:
                return True
            return False
        key = (v.hour, v.minute, v.second)
        if self._min_value is not None:
            m = self._min_value
            if key < (m.hour, m.minute, m.second):
                return True
        if self._max_value is not None:
            m = self._max_value
            if key > (m.hour, m.minute, m.second):
                return True
        return False


__all__ = ["DateFieldState"]
