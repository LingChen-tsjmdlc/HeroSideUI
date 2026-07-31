"""DateInput 纯逻辑层测试（_value / _pattern / _field_state）。

不依赖 Qt，验证值原语、段序解析与段编辑状态机——这是本组件正确性的
主要保障。视觉由 examples 人工验证。
"""

import pytest

from hero_side_ui.components.date_input._field_state import DateFieldState
from hero_side_ui.components.date_input._pattern import (
    build_pattern,
    build_segments,
    parse_pattern,
)
from hero_side_ui.components.date_input._value import (
    DateTimeValue,
    clamp_value,
    now,
    parse_absolute_to_local,
    parse_date,
    parse_datetime,
    parse_zoned_datetime,
    today,
)


def _render(state: DateFieldState) -> str:
    """把状态机当前的段列表拼成完整显示文本。"""
    return "".join(
        spec.text
        if spec.is_literal
        else state.segment_text(spec.type, spec.min_digits)
        for spec in state.specs
    )


# ---------------------------------------------------------------- _value


def test_parse_date():
    v = parse_date("2024-04-04")
    assert (v.year, v.month, v.day) == (2024, 4, 4)
    assert v.has_time is False
    assert v.timezone is None


def test_parse_datetime():
    v = parse_datetime("2024-04-04T18:45:22")
    assert (v.hour, v.minute, v.second) == (18, 45, 22)
    assert v.has_time is True
    assert v.timezone is None


def test_parse_zoned_datetime():
    v = parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]")
    assert (v.year, v.month, v.day) == (2022, 11, 7)
    assert (v.hour, v.minute) == (0, 45)
    assert v.timezone == "America/Los_Angeles"
    assert v.has_time is True


def test_parse_absolute_to_local_shifts_timezone():
    v = parse_absolute_to_local("2021-04-07T18:45:22Z")
    # 转到本机时区后必然带时区且带时间，具体时刻依赖运行环境
    assert v.timezone is not None
    assert v.has_time is True


def test_today_and_now():
    assert today().has_time is False
    n = now("America/New_York")
    assert n.has_time is True
    assert n.timezone == "America/New_York"


def test_with_fields_truncates_overflow_day():
    # 1/31 改成 2 月应截断到当月末日，而不是滚到 3 月
    assert parse_date("2024-01-31").with_fields(month=2).day == 29
    assert parse_date("2023-01-31").with_fields(month=2).day == 28


def test_with_fields_handles_leap_year_switch():
    assert parse_date("2024-02-29").with_fields(year=2023).day == 28


def test_comparison():
    assert parse_date("2024-01-01") < parse_date("2024-06-01")
    assert parse_date("2024-06-01") > parse_date("2024-01-01")
    assert parse_date("2024-01-01") <= parse_date("2024-01-01")


def test_comparison_includes_time():
    a = parse_datetime("2024-04-04T08:00:00")
    b = parse_datetime("2024-04-04T20:00:00")
    assert a < b


def test_clamp_value():
    lo, hi = parse_date("2024-04-10"), parse_date("2024-04-20")
    assert clamp_value(parse_date("2024-04-03"), lo, hi) == lo
    assert clamp_value(parse_date("2024-04-25"), lo, hi) == hi
    mid = parse_date("2024-04-15")
    assert clamp_value(mid, lo, hi) == mid


def test_to_calendar_preserves_instant():
    g = parse_date("2024-04-04")
    indian = g.to_calendar("indian")
    assert indian.identifier == "indian"
    # 转回公历应还原
    assert indian.to_calendar("gregorian").date.is_same_day(g.date)


def test_format():
    assert parse_date("2024-04-04").format("yMd") == "4/4/2024"


def test_value_is_hashable():
    # frozen dataclass 应可当 dict key / set 成员
    assert len({parse_date("2024-04-04"), parse_date("2024-04-04")}) == 1


# ---------------------------------------------------------------- _pattern


def test_build_pattern_varies_by_locale():
    assert build_pattern(locale="en_US") == "M/d/y"
    assert build_pattern(locale="de_DE") == "d.M.y"
    assert build_pattern(locale="ja_JP") == "y/M/d"


def test_parse_pattern_splits_fields_and_literals():
    specs = parse_pattern("M/d/y")
    assert [s.type for s in specs] == ["month", "literal", "day", "literal", "year"]


def test_segment_order_follows_locale():
    def editable(locale):
        return [s.type for s in build_segments(locale=locale) if s.is_editable]

    assert editable("en_US") == ["month", "day", "year"]
    assert editable("de_DE") == ["day", "month", "year"]
    assert editable("ja_JP") == ["year", "month", "day"]


@pytest.mark.parametrize(
    "granularity,expected_tail",
    [
        ("day", []),
        ("hour", ["hour", "dayPeriod"]),
        ("minute", ["hour", "minute", "dayPeriod"]),
        ("second", ["hour", "minute", "second", "dayPeriod"]),
    ],
)
def test_granularity_adds_time_segments(granularity, expected_tail):
    types = [
        s.type for s in build_segments(locale="en_US", granularity=granularity)
        if s.is_editable
    ]
    assert types[:3] == ["month", "day", "year"]
    assert sorted(types[3:]) == sorted(expected_tail)


def test_hour_cycle_24_drops_day_period():
    types = [
        s.type
        for s in build_segments(locale="en_US", granularity="minute", hour_cycle=24)
        if s.is_editable
    ]
    assert "dayPeriod" not in types


def test_timezone_segment_present_only_when_zoned():
    with_tz = [
        s.type
        for s in build_segments(
            locale="en_US", granularity="minute", has_timezone=True
        )
    ]
    assert "timeZone" in with_tz

    hidden = [
        s.type
        for s in build_segments(
            locale="en_US",
            granularity="minute",
            has_timezone=True,
            hide_time_zone=True,
        )
    ]
    assert "timeZone" not in hidden


def test_era_segment_for_indian_calendar():
    types = [s.type for s in build_segments(locale="hi_IN", identifier="indian")]
    assert "era" in types


def test_no_dangling_literals():
    specs = build_segments(locale="en_US", granularity="minute", hour_cycle=24)
    assert not specs[0].is_literal
    assert not specs[-1].is_literal


def test_invalid_granularity_rejected():
    with pytest.raises(ValueError):
        build_pattern(granularity="fortnight")


# ------------------------------------------------------------ _field_state


def test_placeholder_rendering():
    st = DateFieldState(placeholder_value=parse_date("1995-11-06"))
    assert _render(st) == "mm/dd/yyyy"
    assert st.value() is None
    assert st.is_complete() is False


def test_set_value_fills_segments():
    st = DateFieldState(value=parse_date("2024-04-04"))
    assert _render(st) == "04/04/2024"
    assert st.value() == parse_date("2024-04-04")
    assert st.is_complete() is True


def test_typing_year_digit_by_digit_is_not_clamped():
    """逐位输入年份的中间态不能被 min_value 夹住。

    若 append_digit 走 clamp，输入 "2" 会立刻变成 1900，四位年份根本
    输不进去 —— 这是本组件最容易踩的坑。
    """
    st = DateFieldState(
        min_value=parse_date("1900-01-01"), max_value=parse_date("2099-12-31")
    )
    for digit in (2, 0, 2, 4):
        st.append_digit("year", digit)
    assert st.segment_text("year", 1) == "2024"


def test_typing_advances_when_segment_full():
    st = DateFieldState()
    assert st.append_digit("month", 1) is False
    assert st.append_digit("month", 2) is True
    assert st.segment_text("month", 1) == "12"


def test_typing_single_digit_completes_when_next_would_overflow():
    # 月份输 9 后再输一位必然溢出，应立即视为完成
    st = DateFieldState()
    assert st.append_digit("month", 9) is True
    assert st.segment_text("month", 1) == "09"


def test_typing_overflow_restarts():
    st = DateFieldState()
    st.append_digit("day", 3)
    st.append_digit("day", 9)  # 39 越界，应重新从 9 开始
    assert st.segment_text("day", 1) == "09"


def test_increment_wraps_around():
    st = DateFieldState(value=parse_date("2024-12-15"))
    st.increment("month", 1)
    assert st.segment_text("month", 1) == "01"
    st.increment("month", -1)
    assert st.segment_text("month", 1) == "12"


def test_increment_from_placeholder_uses_placeholder_base():
    st = DateFieldState(placeholder_value=parse_date("1995-11-06"))
    st.increment("month", 1)
    # 从占位值 11 月起步 +1 → 12 月，而不是从 0 起步
    assert st.segment_text("month", 1) == "12"


def test_changing_month_truncates_day():
    st = DateFieldState(value=parse_date("2024-01-31"))
    st._set_segment("month", 2)
    assert st.segment_text("day", 1) == "29"


def test_clear_segment_makes_value_none():
    st = DateFieldState(value=parse_date("2024-04-04"))
    st.clear_segment("month")
    assert st.is_placeholder("month") is True
    assert st.value() is None


def test_clear_resets_all():
    st = DateFieldState(value=parse_date("2024-04-04"))
    st.clear()
    assert _render(st) == "mm/dd/yyyy"


def test_day_period_toggle_shifts_hour():
    st = DateFieldState(
        value=parse_datetime("2024-04-04T09:30:00"), granularity="minute"
    )
    assert st.value().hour == 9
    st.increment("dayPeriod", 1)
    assert st.value().hour == 21


def test_hour_cycle_24_renders_zero_hour():
    st = DateFieldState(
        value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
        granularity="minute",
        hour_cycle=24,
    )
    assert "00:45" in _render(st)


def test_hour_cycle_12_renders_twelve_am():
    st = DateFieldState(
        value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
        granularity="minute",
    )
    assert "12:45" in _render(st)


def test_timezone_segment_text():
    st = DateFieldState(
        value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
        granularity="minute",
    )
    assert st.segment_text("timeZone") == "PST"


def test_derived_segments_not_placeholder_once_dependency_filled():
    """AM/PM 不该在时间已填时仍显示为占位色。"""
    st = DateFieldState(
        value=parse_datetime("2024-04-04T09:30:00"), granularity="minute"
    )
    assert st.is_placeholder("dayPeriod") is False
    assert st.is_placeholder("timeZone") is False


def test_is_invalid_detects_out_of_range():
    st = DateFieldState(
        value=parse_date("2024-04-03"), min_value=parse_date("2024-04-10")
    )
    assert st.is_invalid() is True

    ok = DateFieldState(
        value=parse_date("2024-04-15"), min_value=parse_date("2024-04-10")
    )
    assert ok.is_invalid() is False


def test_commit_segment_clamps_into_range():
    st = DateFieldState()
    st._set_segment("month", 99)
    st.commit_segment("month")
    assert st.segment_text("month", 1) == "12"


def test_segment_range_day_depends_on_month():
    st = DateFieldState(value=parse_date("2024-02-10"))
    assert st.segment_range("day") == (1, 29)
    st._set_segment("month", 1)
    assert st.segment_range("day") == (1, 31)


def test_editable_types_excludes_literals_and_timezone():
    st = DateFieldState(
        value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
        granularity="minute",
    )
    assert "literal" not in st.editable_types
    assert "timeZone" not in st.editable_types


def test_leading_zeros_can_be_disabled():
    st = DateFieldState(
        value=parse_date("2024-04-04"), should_force_leading_zeros=False
    )
    assert st.segment_text("month", 1) == "4"


def test_era_year_not_zero_padded():
    """带 era 的历法年份是纪元相对值，不该补成 4 位。"""
    st = DateFieldState(
        value=parse_absolute_to_local("2021-04-07T18:45:22Z"),
        locale="ja_JP",
        identifier="japanese",
    )
    assert "0003" not in _render(st)


def test_indian_calendar_uses_own_era_name():
    """DateFormatSymbols 单参重载会错拿公历 BC/AD，必须走两参重载。"""
    st = DateFieldState(
        value=parse_absolute_to_local("2021-04-07T18:45:22Z"),
        locale="hi_IN",
        identifier="indian",
    )
    assert st.segment_text("era") not in ("BC", "AD")


def test_has_any_input():
    st = DateFieldState()
    assert st.has_any_input() is False
    st.append_digit("month", 1)
    assert st.has_any_input() is True
