"""RangeCalendar 渲染层测试（P5：范围日历）。

范围锚定、hover 预览、信号；纯日期逻辑见 test_calendar_logic.py。
"""

import pytest

from hero_side_ui import RangeCalendar
from hero_side_ui.components.calendar._date import CalendarDate


def _make(qtbot, **kwargs) -> RangeCalendar:
    c = RangeCalendar(**kwargs)
    qtbot.addWidget(c)
    return c


def test_construct_default(qtbot):
    c = _make(qtbot)
    assert c.value() is None


def test_preset_range(qtbot):
    v = (CalendarDate(2026, 7, 8), CalendarDate(2026, 7, 20))
    c = _make(qtbot, value=v)
    got = c.value()
    assert got[0].is_same_day(v[0])
    assert got[1].is_same_day(v[1])


def test_two_click_selects_range(qtbot):
    c = _make(qtbot)
    received = []
    c.change.connect(received.append)
    c._on_date_clicked(CalendarDate(2026, 7, 5))
    assert c.value() is None  # 锚定中
    c._on_date_clicked(CalendarDate(2026, 7, 15))
    got = c.value()
    assert got[0].is_same_day(CalendarDate(2026, 7, 5))
    assert got[1].is_same_day(CalendarDate(2026, 7, 15))
    assert len(received) == 1


def test_reverse_order_sorted(qtbot):
    c = _make(qtbot)
    c._on_date_clicked(CalendarDate(2026, 7, 20))
    c._on_date_clicked(CalendarDate(2026, 7, 10))
    got = c.value()
    assert got[0].is_same_day(CalendarDate(2026, 7, 10))
    assert got[1].is_same_day(CalendarDate(2026, 7, 20))


def test_hover_preview(qtbot):
    c = _make(qtbot)
    c._on_date_clicked(CalendarDate(2026, 7, 10))  # 锚定
    c._on_date_hovered(CalendarDate(2026, 7, 15))
    rng = c._state.highlighted_range()
    assert rng[0].is_same_day(CalendarDate(2026, 7, 10))
    assert rng[1].is_same_day(CalendarDate(2026, 7, 15))


def test_is_range_flag(qtbot):
    c = _make(qtbot)
    assert c._state.is_range() is True


def test_range_multi_month(qtbot):
    c = _make(qtbot, visible_months=2)
    assert len(c._months) == 2


# ---- 边界组合：picker × range / multi-month ----

def test_pickers_disabled_when_multi_month(qtbot):
    # 月/年选择器仅单月生效，多月时强制关闭且不可展开
    c = _make(qtbot, show_month_and_year_pickers=True, visible_months=2)
    assert c._show_pickers is False
    assert c._picker is None
    c.set_header_expanded(True)
    assert c.is_header_expanded() is False


def test_pickers_with_range_preserve_value(qtbot):
    # range + 单月 picker：展开→改月→收起，已确定的 range 值不被搅乱
    v = (CalendarDate(2026, 7, 8), CalendarDate(2026, 7, 20))
    c = _make(qtbot, show_month_and_year_pickers=True, value=v)
    assert c._show_pickers is True and c._picker is not None
    c.set_header_expanded(True)
    c._on_picker_month(9)                      # picker 改月只动 focused
    assert c._state.focused_date.month == 9
    assert c.value()[0].is_same_day(v[0])      # range 值保持
    assert c.value()[1].is_same_day(v[1])
    c.set_header_expanded(False)
    assert c.is_header_expanded() is False

