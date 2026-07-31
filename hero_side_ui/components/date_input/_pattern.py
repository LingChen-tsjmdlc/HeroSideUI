"""段序解析：把 ICU 日期 pattern 拆成 DateInput 的段列表（零 Qt 依赖）。

段顺序绝不硬编码——由 ICU DateTimePatternGenerator 按 locale + 历法
推导出 best pattern（en_US 得 M/d/y、de_DE 得 d.M.y、ja_JP 得 y/M/d），
再逐字符扫描 pattern，把字段字母转成段、把其余字符转成字面量分隔符。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

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
EDITABLE_TYPES = frozenset(
    {"era", "year", "month", "day", "hour", "minute", "second", "dayPeriod"}
)

VALID_GRANULARITIES = ("day", "hour", "minute", "second")


@dataclass(frozen=True)
class SegmentSpec:
    """一个段或字面量在段列表中的静态描述。

    :param type: 段类型；字面量为 "literal"
    :param text: 字面量文本（仅 literal 使用）
    :param min_digits: 该段最少显示位数（由 pattern 中字母重复次数决定）
    """

    type: str
    text: str = ""
    min_digits: int = 1

    @property
    def is_editable(self) -> bool:
        return self.type in EDITABLE_TYPES

    @property
    def is_literal(self) -> bool:
        return self.type == "literal"


def build_pattern(
    *,
    locale: str = "en_US",
    identifier: str = "gregorian",
    granularity: str = "day",
    hour_cycle: Optional[int] = None,
) -> str:
    """按 locale/历法/粒度/小时制求 ICU best pattern。

    :param hour_cycle: 12 或 24；None 表示跟随 locale 习惯（skeleton 用 j）
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
    return gen.getBestPattern("yMd" + time_part)


def parse_pattern(pattern: str) -> List[SegmentSpec]:
    """把 ICU pattern 字符串扫描成段/字面量序列。

    ICU pattern 中单引号包裹的是字面量（如 de_DE 的 'um'），需原样保留。
    """
    specs: List[SegmentSpec] = []
    buffer: List[str] = []

    def flush_literal():
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
    hour_cycle: Optional[int] = None,
    hide_time_zone: bool = False,
    has_timezone: bool = False,
) -> List[SegmentSpec]:
    """求最终段列表：解析 pattern 后按需补/删时区段。

    ICU 的 yMd 系 skeleton 不含时区字段，带时区的值需要额外补一个 timeZone
    段（对齐 HeroUI 在 ZonedDateTime 下显示 PST 的行为）。
    """
    specs = parse_pattern(
        build_pattern(
            locale=locale,
            identifier=identifier,
            granularity=granularity,
            hour_cycle=hour_cycle,
        )
    )

    if has_timezone and not hide_time_zone and granularity != "day":
        specs = specs + [SegmentSpec("literal", text=" "), SegmentSpec("timeZone")]
    else:
        specs = [s for s in specs if s.type != "timeZone"]

    return _strip_dangling_literals(specs)


def _strip_dangling_literals(specs: List[SegmentSpec]) -> List[SegmentSpec]:
    """去掉首尾多余的字面量与因删段而产生的连续分隔符。"""
    out: List[SegmentSpec] = []
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
    "VALID_GRANULARITIES",
    "SegmentSpec",
    "build_pattern",
    "build_segments",
    "parse_pattern",
]
