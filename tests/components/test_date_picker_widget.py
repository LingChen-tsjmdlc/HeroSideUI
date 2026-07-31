"""DatePicker / DateRangePicker 渲染层测试。

构造 / 值同步 / 信号 / 禁用 / 弹层开关 / 范围反向，走 pytest-qt。
纯逻辑（状态机、值原语、日历网格）见对应 logic 测试。
"""

import pytest

from hero_side_ui import DatePicker, DateRangePicker, parse_date


def _make(qtbot, **kwargs) -> DatePicker:
    kw = {"disable_animation": True}
    kw.update(kwargs)
    w = DatePicker(**kw)
    qtbot.addWidget(w)
    return w


def _make_range(qtbot, **kwargs) -> DateRangePicker:
    kw = {"disable_animation": True}
    kw.update(kwargs)
    w = DateRangePicker(**kw)
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------- DatePicker 构造

def test_construct_default(qtbot):
    dp = _make(qtbot)
    assert dp.value() is None
    assert dp.is_calendar_open() is False


def test_construct_with_value(qtbot):
    v = parse_date("2024-04-04")
    dp = _make(qtbot, value=v)
    assert dp.value() == v


def test_selector_button_is_button(qtbot):
    dp = _make(qtbot)
    assert dp._selector_btn is not None
    assert dp.date_input is not None


def test_selector_placement_start_vs_end(qtbot):
    end = _make(qtbot, selector_button_placement="end")
    start = _make(qtbot, selector_button_placement="start")
    # 两者都注入了日历按钮，只是槽位不同
    assert end._selector_btn is not None
    assert start._selector_btn is not None


# ---------------------------------------------------------------- 值同步

def test_set_value_roundtrip(qtbot):
    dp = _make(qtbot)
    v = parse_date("2025-12-31")
    dp.set_value(v)
    assert dp.value() == v
    # 日历高亮也应同步
    assert dp.calendar_widget.value() == v.date


def test_clear(qtbot):
    dp = _make(qtbot, value=parse_date("2024-04-04"))
    dp.clear()
    assert dp.value() is None


def test_set_value_emits_value_changed(qtbot):
    dp = _make(qtbot)
    seen = []
    dp.value_changed.connect(seen.append)
    v = parse_date("2024-04-04")
    dp.set_value(v)
    assert seen == [v]


# ---------------------------------------------------------------- 禁用

def test_disabled_getter_setter(qtbot):
    dp = _make(qtbot, is_disabled=True)
    assert dp.is_disabled() is True
    dp.set_is_disabled(False)
    assert dp.is_disabled() is False
    # 禁用时按钮也失效
    assert dp._selector_btn.isEnabled() is True
    dp.set_is_disabled(True)
    assert dp._selector_btn.isEnabled() is False


def test_disabled_blocks_open_calendar(qtbot):
    dp = _make(qtbot, is_disabled=True)
    dp.open_calendar()
    assert dp.is_calendar_open() is False


# ---------------------------------------------------------------- 弹层开关

def test_open_close_calendar(qtbot):
    dp = _make(qtbot)
    dp.open_calendar()
    assert dp.is_calendar_open() is True
    dp.close_calendar()
    assert dp.is_calendar_open() is False


def test_selector_click_toggles_calendar(qtbot):
    dp = _make(qtbot)
    dp._on_selector_click()
    assert dp.is_calendar_open() is True
    dp._on_selector_click()
    assert dp.is_calendar_open() is False


# ---------------------------------------------------------------- 日历选择写回

def test_calendar_change_writes_back(qtbot):
    dp = _make(qtbot)
    cal = dp.calendar_widget
    target = parse_date("2026-06-15").date
    dp._on_calendar_change(target)
    assert dp.value() == parse_date("2026-06-15")


# ---------------------------------------------------------------- DateRangePicker

def test_range_construct_default(qtbot):
    drp = _make_range(qtbot)
    assert drp.value() == (None, None)


def test_range_construct_with_values(qtbot):
    s = parse_date("2024-04-01")
    e = parse_date("2024-04-10")
    drp = _make_range(qtbot, start_value=s, end_value=e)
    assert drp.value() == (s, e)


def test_range_set_value_roundtrip(qtbot):
    drp = _make_range(qtbot)
    s = parse_date("2024-05-01")
    e = parse_date("2024-05-10")
    drp.set_value((s, e))
    assert drp.value() == (s, e)
    # 范围日历也应同步
    assert drp.calendar_widget.value() == (s.date, e.date)


def test_range_clear(qtbot):
    drp = _make_range(
        qtbot,
        start_value=parse_date("2024-04-01"),
        end_value=parse_date("2024-04-10"),
    )
    drp.clear()
    assert drp.value() == (None, None)


def test_range_calendar_change_writes_back(qtbot):
    drp = _make_range(qtbot)
    start = parse_date("2024-04-01").date
    end = parse_date("2024-04-10").date
    drp._on_calendar_change((start, end))
    assert drp.value() == (
        parse_date("2024-04-01"),
        parse_date("2024-04-10"),
    )


def test_range_reversed_is_invalid(qtbot):
    drp = _make_range(qtbot)
    s = parse_date("2024-04-10")
    e = parse_date("2024-04-01")  # 结束早于开始
    drp.set_range_value((s, e))
    assert drp.date_field._is_reversed() is True
    assert drp.date_field._is_invalid is True


def test_range_disabled_getter_setter(qtbot):
    drp = _make_range(qtbot, is_disabled=True)
    assert drp.is_disabled() is True
    drp.set_is_disabled(False)
    assert drp.is_disabled() is False
