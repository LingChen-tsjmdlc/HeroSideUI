"""段编辑状态机：复刻 react-stately 的 useDateFieldState（零 Qt 依赖）。

职责：持有"每个可编辑段当前值 / 是否仍是占位态"，把键盘动作（逐位输入、
上下键增减、删除）翻译成新的段值，并在所有段都填好后合成出对外的
DateTimeValue。段序完全交给 ``_pattern`` 决定，本文件只管值的推演。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional

import icu

from ..calendar._date import CalendarDate, _fresh_calendar, _locale_for
from ._pattern import SegmentSpec, build_segments
from ._value import DateTimeValue, _locale_for_locale, clamp_value

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
    """该历法的纪元名列表。

    必须走 ``DateFormatSymbols(locale, calendar_type)`` 两参重载：单参重载
    会无视 locale 里的 @calendar= 关键字，印度历会错拿到公历的 BC/AD。
    """
    loc = _locale_for_locale(locale, identifier)
    try:
        return tuple(str(e) for e in icu.DateFormatSymbols(loc, identifier).getEras())
    except Exception:
        return tuple(str(e) for e in icu.DateFormatSymbols(loc).getEras())


class DateFieldState:
    """DateInput 的段编辑状态机。

    :param value: 受控初始值；None 表示全占位
    :param placeholder_value: 决定占位时各段的"起点"值（如年份从哪年开始增减）
    :param granularity: day/hour/minute/second
    :param hour_cycle: 12 或 24；None 跟随 locale
    :param locale: ICU locale 字符串
    :param identifier: ICU 历法标识
    :param min_value / max_value: 值域约束，段提交时 clamp
    :param hide_time_zone: 隐藏时区段
    :param should_force_leading_zeros: 数字段补前导零
    """

    def __init__(
        self,
        *,
        value: Optional[DateTimeValue] = None,
        placeholder_value: Optional[DateTimeValue] = None,
        granularity: str = "day",
        hour_cycle: Optional[int] = None,
        locale: str = "en_US",
        identifier: str = "gregorian",
        min_value: Optional[DateTimeValue] = None,
        max_value: Optional[DateTimeValue] = None,
        hide_time_zone: bool = False,
        should_force_leading_zeros: bool = True,
    ):
        self._granularity = granularity
        self._hour_cycle = hour_cycle
        self._locale = locale
        self._identifier = identifier
        self._min_value = min_value
        self._max_value = max_value
        self._hide_time_zone = hide_time_zone
        self._force_zeros = should_force_leading_zeros

        # 占位起点：优先 placeholder_value，其次今天
        base = placeholder_value or DateTimeValue.from_date(
            CalendarDate.today(identifier)
        )
        self._placeholder = base.to_calendar(identifier)

        # 时区取自值或占位值（决定是否出现 timeZone 段）
        self._timezone = None
        if value is not None and value.timezone:
            self._timezone = value.timezone
        elif placeholder_value is not None and placeholder_value.timezone:
            self._timezone = placeholder_value.timezone

        self._specs: List[SegmentSpec] = build_segments(
            locale=locale,
            identifier=identifier,
            granularity=granularity,
            hour_cycle=hour_cycle,
            hide_time_zone=hide_time_zone,
            has_timezone=self._timezone is not None,
        )

        # 段值表：type → int；缺席即占位态
        self._values: Dict[str, int] = {}
        if value is not None:
            self.set_value(value)

    # ============================================================
    # 结构查询
    # ============================================================
    @property
    def specs(self) -> List[SegmentSpec]:
        return self._specs

    @property
    def granularity(self) -> str:
        return self._granularity

    @property
    def timezone(self) -> Optional[str]:
        return self._timezone

    @property
    def editable_types(self) -> List[str]:
        return [s.type for s in self._specs if s.is_editable]

    def is_placeholder(self, seg_type: str) -> bool:
        """该段是否仍是未填写的占位态。

        era / dayPeriod / timeZone 是派生段（分别由年份、小时、时区决定），
        用户从不直接"填"它们；只要其依赖段已填就该按已填写着色，
        否则会出现"04/04/2024 已填但 AM 仍是灰色"的割裂感。
        """
        if seg_type == "timeZone":
            return False
        if seg_type == "dayPeriod":
            return "hour" not in self._values and "dayPeriod" not in self._values
        if seg_type == "era":
            return "year" not in self._values and "era" not in self._values
        return seg_type not in self._values

    def has_any_input(self) -> bool:
        """是否至少填了一个段（用于 label 浮起判断）。"""
        return bool(self._values)

    def is_complete(self) -> bool:
        """所有可编辑段是否都已填（era/dayPeriod 有默认值不算必填）。"""
        return all(
            t in self._values
            for t in self.editable_types
            if t not in ("era", "dayPeriod", "timeZone")
        )

    # ============================================================
    # 值读写
    # ============================================================
    def value(self) -> Optional[DateTimeValue]:
        """段全填好时返回值对象，否则 None（对齐 HeroUI 的 null 语义）。"""
        if not self.is_complete():
            return None
        return self._compose()

    def set_value(self, value: Optional[DateTimeValue]) -> None:
        """外部受控赋值：拆解成各段值。"""
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
        self._values.clear()

    def clear_segment(self, seg_type: str) -> None:
        self._values.pop(seg_type, None)

    def _compose(self) -> DateTimeValue:
        """把当前段值合成 DateTimeValue（不做 clamp）。

        hour 段内部始终存 24 小时值（_set_segment 已按 dayPeriod 归一），
        此处直接取用即可。
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
            second=self._values.get("second", 0)
            if self._granularity == "second"
            else 0,
            identifier=self._identifier,
            timezone=self._timezone,
            has_time=self._granularity != "day",
        )

    # ============================================================
    # 段的显示文本
    # ============================================================
    def segment_text(self, seg_type: str, min_digits: int = 1) -> str:
        """段的显示文本；占位态返回 mm/dd/yyyy 之类的提示符。"""
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
        """段的显示宽度：年 4 位，其余至少 2 位（对齐 HeroUI 视觉）。

        带 era 段的历法（日本年号等）年份是纪元相对值、天然是小数字，
        补到 4 位会显示成 令和0003，故此时按 pattern 原始位数走。
        """
        if seg_type == "year":
            return min_digits if self._has_era_segment() else 4
        return max(2, min_digits)

    def _has_era_segment(self) -> bool:
        return any(s.type == "era" for s in self._specs)

    def _timezone_text(self) -> str:
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
        eras = _era_names(self._locale, self._identifier)
        idx = self._values.get("era")
        if idx is None:
            cal = self._compose().date._to_icu()
            idx = cal.get(icu.Calendar.ERA)
        return str(eras[idx]) if 0 <= idx < len(eras) else ""

    def _day_period_text(self) -> str:
        sym = icu.DateFormatSymbols(_locale_for_locale(self._locale, self._identifier))
        ampm = list(sym.getAmPmStrings())
        pm = self._values.get("dayPeriod")
        if pm is None:
            pm = 1 if self._values.get("hour", self._placeholder.hour) >= 12 else 0
        return str(ampm[1] if pm else ampm[0])    # ============================================================
    # 编辑动作
    # ============================================================
    def _is_hour12(self) -> bool:
        """当前是否 12 小时制（有 dayPeriod 段即为 12 小时制）。"""
        return any(s.type == "dayPeriod" for s in self._specs)

    def segment_range(self, seg_type: str) -> tuple:
        """段的合法取值区间（闭区间）。

        month/day 的上界依赖当前年月，故基于已填段实时计算。
        """
        if seg_type == "year":
            lo = self._min_value.year if self._min_value else 1
            hi = self._max_value.year if self._max_value else 9999
            return lo, hi
        if seg_type == "month":
            return 1, 12
        if seg_type == "day":
            cur = self._compose()
            return 1, CalendarDate(
                cur.year, cur.month, 1, self._identifier
            ).days_in_month
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
        """上下键增减，越界回绕（对齐 react-aria 的 cycle 行为）。"""
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
        """写入段值并做跨段一致性修正（如 2 月 31 日截成 29）。"""
        if seg_type == "hour" and self._is_hour12():
            # 12 小时制下用户输的是 1~12，需按当前半天归属还原成 24 小时值
            prev_hour = self._values.get("hour", self._placeholder.hour)
            pm = self._values.get("dayPeriod", 1 if prev_hour >= 12 else 0)
            raw = (raw % 12) + (12 if pm else 0)
        elif seg_type == "dayPeriod":
            # 切换半天时直接把已有 hour 搬到另一半天，避免二者不一致
            self._values[seg_type] = raw
            if "hour" in self._values:
                self._values["hour"] = (self._values["hour"] % 12) + (
                    12 if raw else 0
                )
            return
        self._values[seg_type] = raw

        # 改年/月后，日可能超过当月天数 → 截断
        if seg_type in ("year", "month") and "day" in self._values:
            cur = self._compose()
            max_day = CalendarDate(
                cur.year, cur.month, 1, self._identifier
            ).days_in_month
            if self._values["day"] > max_day:
                self._values["day"] = max_day

    def append_digit(self, seg_type: str, digit: int) -> bool:
        """逐位输入一个数字，返回该段是否已输满（供调用方自动跳下一段）。

        中间态（如 year 段刚输入 "2"）绝不能走 clamp——否则 "2" 会被
        min_value 夹成 1900，用户根本输不进四位年份。故此处只做范围上界
        的溢出判断，真正的 clamp 留到段提交（focus out / 切段）时。
        """
        if seg_type in ("timeZone", "era", "dayPeriod"):
            return False
        lo, hi = self.segment_range(seg_type)
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
        """段编辑结束：把该段夹进自身合法范围（如月份 99 → 12）。

        只约束单段自身的物理范围，不把整体值拉进 [min_value, max_value] ——
        HeroUI 对越界日期的处理是标红提示而非静默改写用户输入。
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
        """值是否越界（供组件同步 invalid 视觉）。"""
        v = self.value()
        if v is None:
            return False
        if self._min_value is not None and v < self._min_value:
            return True
        if self._max_value is not None and v > self._max_value:
            return True
        return False


__all__ = ["DateFieldState"]
