"""段序解析：由 ICU 按 locale/历法推导 best pattern 再拆成段列表。

段顺序不硬编码（en_US 得 M/d/y、de_DE 得 d.M.y）；字段字母转段、
其余字符转字面量分隔符。
"""

from __future__ import annotations

from dataclasses import dataclass

import icu

from ._value import _locale_for_locale

# ICU pattern 字段字母 → 段类型
_FIELD_LETTERS = {
    "G": "era",
    "y": "year",
    "u": "year",
    "Y": "year",
    "M": "month",
    "L": "month",
    "d": "day",
    "h": "hour",
    "H": "hour",
    "K": "hour",
    "k": "hour",
    "m": "minute",
    "s": "second",
    "a": "dayPeriod",
    "b": "dayPeriod",
    "z": "timeZone",
    "Z": "timeZone",
    "v": "timeZone",
    "V": "timeZone",
}

# granularity → ICU skeleton 的时间部分
_TIME_SKELETON = {
    "day": "",
    "hour": "j",
    "minute": "jm",
    "second": "jms",
}

# 可编辑的段类型（timeZone / 字面量不可编辑）
EDITABLE_TYPES = frozenset({"era", "year", "month", "day", "hour", "minute", "second", "dayPeriod"})

VALID_GRANULARITIES = ("day", "hour", "minute", "second")

# 纯时间粒度（TimeInput 用；不含 day）
TIME_GRANULARITIES = ("hour", "minute", "second")


@dataclass(frozen=True)
class SegmentSpec:
    """段或字面量的静态描述。

    Attributes:
        type: 段类型（era/year/.../literal/timeZone）。
        text: 字面量文本；段类型时为空。
        min_digits: pattern 给出的最少位数。
    """

    type: str
    text: str = ""
    min_digits: int = 1

    @property
    def is_editable(self) -> bool:
        """该段是否可由用户输入。

        Returns:
            type 在 EDITABLE_TYPES 内为 True（字面量与时区不可编辑）。
        """
        return self.type in EDITABLE_TYPES

    @property
    def is_literal(self) -> bool:
        """该段是否为字面量分隔符。

        Returns:
            type == literal 时为 True。
        """
        return self.type == "literal"


def build_pattern(
    *,
    locale: str = "en_US",
    identifier: str = "gregorian",
    granularity: str = "day",
    hour_cycle: int | None = None,
    include_date: bool = True,
) -> str:
    """按 locale/历法/粒度/小时制求 ICU best pattern。

    Args:
        locale: ICU locale。
        identifier: 历法标识。
        granularity: 时间粒度。
        hour_cycle: 12/24；None 跟随 locale（skeleton 用 j）。
        include_date: False 时只求时间 pattern（TimeInput 用）。

    Returns:
        ICU pattern 字符串。

    Raises:
        ValueError: granularity 不在 _TIME_SKELETON 中时抛出。
    """
    if granularity not in _TIME_SKELETON:
        raise ValueError(f"invalid granularity: {granularity!r}")
    time_part = _TIME_SKELETON[granularity]
    if time_part and hour_cycle == 24:
        time_part = time_part.replace("j", "H")
    elif time_part and hour_cycle == 12:
        time_part = time_part.replace("j", "h")

    loc = _locale_for_locale(locale, identifier)
    gen = icu.DateTimePatternGenerator.createInstance(loc)
    return gen.getBestPattern(("yMd" if include_date else "") + time_part)


def parse_pattern(pattern: str) -> list[SegmentSpec]:
    """把 ICU pattern 字符串扫描成段 / 字面量序列。

    Args:
        pattern: ICU 日期时间 pattern 字符串。

    Returns:
        段与字面量的有序列表；连续相同字段字母合并成一个段，
        run 长度（上限 4）作为 min_digits。

    Note:
        单引号包裹的是字面量（如 de_DE 的 'um'），需原样保留；
        连续两个单引号表示一个真实的单引号字符。
    """
    specs: list[SegmentSpec] = []
    buffer: list[str] = []

    def flush_literal():
        """把已累积的字面量字符刷成一个 literal 段。"""
        if buffer:
            specs.append(SegmentSpec("literal", text="".join(buffer)))
            buffer.clear()

    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]

        # 单引号包裹的字面量
        if ch == "'":
            i += 1
            while i < n:
                if pattern[i] == "'":
                    # 连续两个单引号表示一个真实的单引号字符
                    if i + 1 < n and pattern[i + 1] == "'":
                        buffer.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                buffer.append(pattern[i])
                i += 1
            continue

        if ch in _FIELD_LETTERS:
            # 统计连续相同字母的个数 → 决定最少位数
            run = 1
            while i + run < n and pattern[i + run] == ch:
                run += 1
            flush_literal()
            seg_type = _FIELD_LETTERS[ch]
            # 月份 MMM/MMMM 是文本月名，本组件统一按数字段处理，
            # 只有位数信息有意义
            specs.append(SegmentSpec(seg_type, min_digits=min(run, 4)))
            i += run
            continue

        buffer.append(ch)
        i += 1

    flush_literal()
    return specs


def build_segments(
    *,
    locale: str = "en_US",
    identifier: str = "gregorian",
    granularity: str = "day",
    hour_cycle: int | None = None,
    hide_time_zone: bool = False,
    has_timezone: bool = False,
    include_date: bool = True,
) -> list[SegmentSpec]:
    """求最终段列表：解析 pattern 后按需补 / 删时区段。

    Args:
        locale: ICU locale。
        identifier: 历法标识。
        granularity: 时间粒度。
        hour_cycle: 12 / 24；None 跟随 locale。
        hide_time_zone: 强制隐藏时区段。
        has_timezone: 值里是否带时区（决定是否需要 timeZone 段）。
        include_date: False 时只求时间 pattern（TimeInput 用）。

    Returns:
        去掉首尾悬空字面量后的 SegmentSpec 列表。
    """
    specs = parse_pattern(
        build_pattern(
            locale=locale,
            identifier=identifier,
            granularity=granularity,
            hour_cycle=hour_cycle,
            include_date=include_date,
        )
    )

    if has_timezone and not hide_time_zone and granularity != "day":
        specs = [*specs, SegmentSpec("literal", text=" "), SegmentSpec("timeZone")]
    else:
        specs = [s for s in specs if s.type != "timeZone"]

    return _strip_dangling_literals(specs)


def _strip_dangling_literals(specs: list[SegmentSpec]) -> list[SegmentSpec]:
    """去掉首尾多余的字面量与因删段而产生的连续分隔符。

    Args:
        specs: 初步解析出的段列表。

    Returns:
        相邻字面量合并、首尾字面量剥离后的新列表。
    """
    out: list[SegmentSpec] = []
    for spec in specs:
        if spec.is_literal and out and out[-1].is_literal:
            out[-1] = SegmentSpec("literal", text=out[-1].text + spec.text)
            continue
        out.append(spec)
    while out and out[0].is_literal:
        out.pop(0)
    while out and out[-1].is_literal:
        out.pop()
    return out


__all__ = [
    "EDITABLE_TYPES",
    "TIME_GRANULARITIES",
    "VALID_GRANULARITIES",
    "SegmentSpec",
    "build_pattern",
    "build_segments",
    "parse_pattern",
]
