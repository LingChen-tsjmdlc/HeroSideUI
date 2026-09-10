"""TimeInput 组件测试。

段序/状态机等纯逻辑与渲染/键盘/信号测试合并在本文件，
按"逻辑 / 构造 / 渲染 / 键盘 / 越界 / API"分节，风格对齐
test_date_input_widget.py。
"""

import pytest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from hero_side_ui import TimeInput
from hero_side_ui.components.date_input._field_state import DateFieldState
from hero_side_ui.components.date_input._pattern import build_segments
from hero_side_ui.components.date_input._value import (
    DateTimeValue,
    now,
    parse_datetime,
)

_T0930 = parse_datetime("2024-04-04T09:30:00")
_T1345 = parse_datetime("2024-04-04T13:45:00")
_T0905_07 = parse_datetime("2024-04-04T09:05:07")


def _make(qtbot, **kwargs) -> TimeInput:
    ti = TimeInput(**kwargs)
    qtbot.addWidget(ti)
    return ti


def _render(ti: TimeInput) -> str:
    """拼出段行当前显示的完整文本。"""
    parts = []
    for i in range(ti._segment_layout.count()):
        w = ti._segment_layout.itemAt(i).widget()
        if w is not None:
            parts.append(w.text())
    return "".join(parts)


def _segment_types(ti: TimeInput) -> list:
    return [s.seg_type for s in ti._editable_segments()]


def _show_active(qtbot, ti: TimeInput) -> None:
    ti.show()
    qtbot.waitExposed(ti)
    ti.activateWindow()
    ti.raise_()
    qtbot.waitUntil(ti.isActiveWindow, timeout=2000)


# ---------------------------------------------------------------- 逻辑：段序


def test_time_only_segments_have_no_date_fields():
    specs = build_segments(
        granularity="minute", hour_cycle=24, include_date=False
    )
    types = [s.type for s in specs if s.is_editable]
    assert types == ["hour", "minute"]
    assert all(s.type not in ("year", "month", "day") for s in specs)


def test_second_granularity_segments():
    specs = build_segments(
        granularity="second", hour_cycle=24, include_date=False
    )
    types = [s.type for s in specs if s.is_editable]
    assert types == ["hour", "minute", "second"]


def test_twelve_hour_cycle_has_day_period():
    specs = build_segments(
        granularity="minute", hour_cycle=12, include_date=False
    )
    types = [s.type for s in specs if s.is_editable]
    assert "dayPeriod" in types
    assert types.index("hour") < types.index("dayPeriod")


def test_time_only_state_is_complete_without_date():
    state = DateFieldState(
        value=_T0930, granularity="minute", hour_cycle=24, include_date=False
    )
    assert state.is_complete()
    assert state.value() == _T0930


def test_time_only_invalid_compares_time_only():
    lo = parse_datetime("2000-01-01T09:00:00")
    hi = parse_datetime("2000-01-01T18:00:00")

    inside = DateFieldState(
        value=parse_datetime("2099-12-31T12:00:00"),
        granularity="minute",
        hour_cycle=24,
        min_value=lo,
        max_value=hi,
        include_date=False,
    )
    assert not inside.is_invalid()

    late = DateFieldState(
        value=parse_datetime("2000-01-01T20:00:00"),
        granularity="minute",
        hour_cycle=24,
        min_value=lo,
        max_value=hi,
        include_date=False,
    )
    assert late.is_invalid()

    early = DateFieldState(
        value=parse_datetime("2000-01-01T08:00:00"),
        granularity="minute",
        hour_cycle=24,
        min_value=lo,
        max_value=hi,
        include_date=False,
    )
    assert early.is_invalid()


# ---------------------------------------------------------------- 构造


def test_construct_default(qtbot):
    ti = _make(qtbot)
    assert ti.value() is None
    assert ti.objectName() == "heroTimeInput"


def test_default_granularity_is_minute(qtbot):
    ti = _make(qtbot)
    assert ti._granularity == "minute"
    # en_US 默认 12 小时制，jm pattern 带 AM/PM 段
    assert _segment_types(ti) == ["hour", "minute", "dayPeriod"]


def test_placeholder_defaults_to_current_time(qtbot):
    ti = _make(qtbot)
    ph = ti._state._placeholder
    assert ph.has_time
    assert ph.timezone is None
    # 与当前时刻同分（占位起点是 now，而非 0 点）
    assert (ph.hour, ph.minute) == (now().hour, now().minute)


def test_invalid_granularity_rejected(qtbot):
    with pytest.raises(ValueError):
        TimeInput(granularity="day")
    with pytest.raises(ValueError):
        TimeInput(granularity="fortnight")


def test_construct_all_variants(qtbot):
    for variant in ("flat", "faded", "bordered", "underlined"):
        assert _make(qtbot, label="x", variant=variant) is not None


def test_construct_all_colors(qtbot):
    for color in (
        "default",
        "primary",
        "secondary",
        "success",
        "warning",
        "danger",
    ):
        assert _make(qtbot, label="x", color=color) is not None


def test_construct_all_sizes(qtbot):
    for size in ("sm", "md", "lg"):
        assert _make(qtbot, label="x", size=size) is not None


# ---------------------------------------------------------------- 渲染


def test_render_24h(qtbot):
    ti = _make(qtbot, hour_cycle=24, value=_T0930)
    assert _render(ti) == "09:30"


# ICU pattern 的 AM/PM 前是窄不换行空格（U+202F），不是普通空格
_NNBSP = "\u202f"


def test_render_12h_with_period(qtbot):
    ti = _make(qtbot, hour_cycle=12, value=_T1345)
    assert _render(ti) == f"01:45{_NNBSP}PM"


def test_render_12h_midnight_is_12(qtbot):
    ti = _make(
        qtbot,
        hour_cycle=12,
        value=parse_datetime("2024-04-04T00:30:00"),
    )
    assert _render(ti) == f"12:30{_NNBSP}AM"


def test_render_second_granularity(qtbot):
    ti = _make(qtbot, hour_cycle=24, granularity="second", value=_T0905_07)
    assert _render(ti) == "09:05:07"


def test_render_placeholder_hint(qtbot):
    ti = _make(qtbot, hour_cycle=24)
    assert _render(ti) == "hh:mm"


def test_leading_zeros_disabled(qtbot):
    ti = _make(
        qtbot,
        hour_cycle=24,
        should_force_leading_zeros=False,
        value=_T0930,
    )
    assert _render(ti) == "9:30"


def test_no_timezone_segment_without_zoned_value(qtbot):
    ti = _make(qtbot, value=_T0930)
    assert "timeZone" not in _segment_types(ti)


# ---------------------------------------------------------------- 键盘


def test_typing_fills_hour_and_advances(qtbot):
    ti = _make(qtbot, hour_cycle=24)
    _show_active(qtbot, ti)

    segs = ti._editable_segments()
    segs[0].setFocus()
    for key in (Qt.Key.Key_2, Qt.Key.Key_3):
        QTest.keyClick(ti.window().focusWidget() or segs[0], key)
    assert ti._editable_segments()[0].text() == "23"
    # 输满后焦点应落到分钟段
    assert ti._editable_segments()[1].hasFocus()


def test_typing_full_time_produces_value(qtbot):
    ti = _make(qtbot, hour_cycle=24)
    _show_active(qtbot, ti)

    segs = ti._editable_segments()
    segs[0].setFocus()
    for key in (Qt.Key.Key_0, Qt.Key.Key_9, Qt.Key.Key_3, Qt.Key.Key_0):
        QTest.keyClick(ti.window().focusWidget() or segs[0], key)
    v = ti.value()
    assert (v.hour, v.minute) == (9, 30)


def test_arrow_up_wraps_minute(qtbot):
    ti = _make(
        qtbot, hour_cycle=24, value=parse_datetime("2024-04-04T09:59:00")
    )
    _show_active(qtbot, ti)

    minute = next(
        s for s in ti._editable_segments() if s.seg_type == "minute"
    )
    minute.setFocus()
    QTest.keyClick(minute, Qt.Key.Key_Up)
    assert minute.text() == "00"


def test_arrow_down_wraps_hour_24h(qtbot):
    ti = _make(
        qtbot, hour_cycle=24, value=parse_datetime("2024-04-04T00:30:00")
    )
    _show_active(qtbot, ti)

    hour = next(s for s in ti._editable_segments() if s.seg_type == "hour")
    hour.setFocus()
    QTest.keyClick(hour, Qt.Key.Key_Down)
    assert hour.text() == "23"


def test_a_p_keys_toggle_day_period(qtbot):
    ti = _make(qtbot, hour_cycle=12, value=_T0930)
    _show_active(qtbot, ti)

    period = next(
        s for s in ti._editable_segments() if s.seg_type == "dayPeriod"
    )
    period.setFocus()
    QTest.keyClick(period, Qt.Key.Key_P)
    assert ti.value().hour == 21
    QTest.keyClick(period, Qt.Key.Key_A)
    assert ti.value().hour == 9


def test_arrow_starts_from_placeholder_value(qtbot):
    """空段按上键应从占位时刻起步增 1，而不是从 0。"""
    ti = _make(qtbot, hour_cycle=24)
    _show_active(qtbot, ti)

    ph_hour = ti._state._placeholder.hour
    hour = next(s for s in ti._editable_segments() if s.seg_type == "hour")
    hour.setFocus()
    QTest.keyClick(hour, Qt.Key.Key_Up)
    assert hour.text() == str((ph_hour + 1) % 24).zfill(2)


# ---------------------------------------------------------------- 越界


def test_min_max_time_marks_invalid(qtbot):
    ti = _make(
        qtbot,
        hour_cycle=24,
        min_value=parse_datetime("2000-01-01T09:00:00"),
        max_value=parse_datetime("2000-01-01T18:00:00"),
    )
    ti.set_value(parse_datetime("2024-04-04T20:00:00"))
    assert ti._is_invalid
    ti.set_value(parse_datetime("2024-04-04T12:00:00"))
    assert not ti._is_invalid


def test_out_of_range_commit_clamps_segment(qtbot):
    ti = _make(qtbot, hour_cycle=24)
    # 模拟越界中间值，提交时必须夹回物理上界（标红是另一条路径的事）
    ti._state._values["minute"] = 99
    ti._state.commit_segment("minute")
    assert ti._state._values["minute"] == 59


# ---------------------------------------------------------------- 状态/API


def test_readonly_ignores_typing(qtbot):
    ti = _make(qtbot, hour_cycle=24, value=_T0930, is_readonly=True)
    _show_active(qtbot, ti)

    seg = ti._editable_segments()[0]
    seg.setFocus()
    QTest.keyClick(seg, Qt.Key.Key_Up)
    assert seg.text() == "09"


def test_disabled_segments_not_focusable(qtbot):
    ti = _make(qtbot, value=_T0930, is_disabled=True)
    assert ti._editable_segments() == []


def test_set_value_and_clear(qtbot):
    ti = _make(qtbot, hour_cycle=24)
    ti.set_value(_T0930)
    assert _render(ti) == "09:30"
    ti.clear()
    assert _render(ti) == "hh:mm"
    assert ti.value() is None


def test_value_changed_on_set_value(qtbot):
    ti = _make(qtbot)
    with qtbot.waitSignal(ti.value_changed, timeout=1000) as blocker:
        ti.set_value(_T0930)
    assert blocker.args[0] == _T0930


def test_value_changed_on_clear(qtbot):
    ti = _make(qtbot, value=_T0930)
    with qtbot.waitSignal(ti.value_changed, timeout=1000) as blocker:
        ti.clear()
    assert blocker.args[0] is None


def test_set_granularity_within_time_only(qtbot):
    ti = _make(qtbot, hour_cycle=24, granularity="second", value=_T0905_07)
    assert _render(ti) == "09:05:07"
    ti.set_granularity("hour")
    assert _segment_types(ti) == ["hour"]
    assert _render(ti) == "09"
    # 降级后再升级：秒在 hour 粒度下已丢失，补 0（与 DateInput 精度行为一致）
    ti.set_granularity("second")
    assert _render(ti) == "09:00:00"


def test_set_hour_cycle_rebuilds_segments(qtbot):
    ti = _make(qtbot, hour_cycle=24, value=_T1345)
    assert _render(ti) == "13:45"
    ti.set_hour_cycle(12)
    assert "dayPeriod" in _segment_types(ti)
    assert _render(ti) == f"01:45{_NNBSP}PM"


def test_zoned_value_shows_timezone(qtbot):
    from hero_side_ui.components.date_input._value import parse_zoned_datetime

    ti = _make(
        qtbot,
        value=parse_zoned_datetime("2024-04-04T09:30:00[America/Los_Angeles]"),
    )
    # 时区段在段列表里，但它是纯展示段、不可编辑（不在 _editable_segments 里）
    assert "timeZone" in [s.type for s in ti._state.specs]
    assert "timeZone" not in _segment_types(ti)
    ti.set_hide_time_zone(True)
    assert "timeZone" not in [s.type for s in ti._state.specs]


def test_value_keeps_date_part_of_set_value(qtbot):
    """值对象原样进出：时间组件不改写日期部分。"""
    ti = _make(qtbot)
    ti.set_value(_T1345)
    assert ti.value() == _T1345


def test_time_of_day_helper_matches_value(qtbot):
    ti = _make(qtbot, hour_cycle=24, value=_T1345)
    v = ti.value()
    assert isinstance(v, DateTimeValue)
    assert (v.hour, v.minute, v.second) == (13, 45, 0)
