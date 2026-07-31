"""Calendar 纯逻辑层测试（_date / _grid / _state / _range_state）。

这些测试不依赖 Qt，只验证日期算术、网格切分、状态机行为，是本组件
正确性的主要保障。视觉/动画由 examples 人工验证。
"""

import pytest

from hero_side_ui.components.calendar._date import (
    CalendarDate,
    normalize_first_day_of_week,
    weeks_in_month,
    months_in_year,
    year_range,
    SUN,
    MON,
)
from hero_side_ui.components.calendar._grid import (
    get_dates_in_week,
    get_weeks,
    compute_cell_state,
)
from hero_side_ui.components.calendar._state import CalendarState
from hero_side_ui.components.calendar._range_state import RangeCalendarState


# ---------------------------------------------------------------- _date

def test_days_in_month():
    assert CalendarDate(2026, 2, 1).days_in_month == 28
    assert CalendarDate(2024, 2, 1).days_in_month == 29  # 闰年
    assert CalendarDate(2026, 7, 1).days_in_month == 31
    assert CalendarDate(2026, 4, 1).days_in_month == 30


def test_add_month_end_rollover():
    # 1/31 + 1 月 应落到 2/28（ICU add 规则）
    d = CalendarDate(2026, 1, 31).add(months=1)
    assert (d.year, d.month, d.day) == (2026, 2, 28)


def test_add_days_cross_month():
    d = CalendarDate(2026, 1, 30).add(days=5)
    assert (d.year, d.month, d.day) == (2026, 2, 4)


def test_add_year():
    d = CalendarDate(2024, 2, 29).add(years=1)  # 闰日 +1 年
    assert (d.year, d.month, d.day) == (2025, 2, 28)


def test_weekday():
    # 2026-07-30 是周四；ICU 周四=5
    assert CalendarDate(2026, 7, 30).weekday == 5


def test_comparison_and_same():
    a = CalendarDate(2026, 7, 1)
    b = CalendarDate(2026, 7, 15)
    assert a < b and b > a and a <= a and a >= a
    assert a.is_same_month(b)
    assert not a.is_same_day(b)
    assert a.is_same_day(CalendarDate(2026, 7, 1))


def test_first_last_of_month():
    d = CalendarDate(2026, 7, 15)
    assert d.first_of_month().day == 1
    assert d.last_of_month().day == 31


def test_normalize_first_day_of_week():
    assert normalize_first_day_of_week(None) == SUN
    assert normalize_first_day_of_week("mon") == MON
    with pytest.raises(ValueError):
        normalize_first_day_of_week("xxx")


def test_weeks_in_month_range():
    # 各月行数应在 4~6 之间，且 2026-02（周日起，1号周日）恰好 4 周
    for m in range(1, 13):
        n = weeks_in_month(CalendarDate(2026, m, 1), SUN)
        assert 4 <= n <= 6
    assert weeks_in_month(CalendarDate(2026, 2, 1), SUN) == 4


# ---------------------------------------------------------------- _grid

def test_get_dates_in_week_lead_padding():
    # 2026-07：7/1 是周三，周日起 → 第一周前 3 格用上月末尾补齐（6/28~6/30）
    week0 = get_dates_in_week(CalendarDate(2026, 7, 1), 0, SUN)
    assert week0[0].month == 6 and week0[0].day == 28  # 上月周日
    assert week0[1].month == 6 and week0[1].day == 29
    assert week0[2].month == 6 and week0[2].day == 30
    assert week0[3].month == 7 and week0[3].day == 1   # 周三放本月 1 号
    assert all(d is not None for d in week0)            # 无空洞


def test_get_weeks_shape():
    weeks = get_weeks(CalendarDate(2026, 7, 1), SUN)
    assert weeks_in_month(CalendarDate(2026, 7, 1), SUN) == len(weeks)
    for row in weeks:
        assert len(row) == 7


def test_get_weeks_fills_adjacent_months():
    # 首尾行用相邻月实际日期补齐，整个矩阵无 None
    weeks = get_weeks(CalendarDate(2026, 7, 1), SUN)
    for row in weeks:
        for d in row:
            assert d is not None
    # 末行应含下月开头（8 月）
    last_row = weeks[-1]
    assert any(d.month == 8 for d in last_row)
    # 首行应含上月末尾（6 月）
    assert any(d.month == 6 for d in weeks[0])


def test_cell_state_empty():
    st = CalendarState()
    today = CalendarDate.today()
    cs = compute_cell_state(None, CalendarDate(2026, 7, 1), st, today)
    assert cs.is_empty and cs.label == ""


# ---------------------------------------------------------------- _state 单选

def test_select_and_change_signal():
    st = CalendarState(value=None)
    fired = []
    st.on_change = fired.append
    target = CalendarDate(2026, 7, 15)
    st.select_date(target)
    assert st.value.is_same_day(target)
    assert len(fired) == 1 and fired[0].is_same_day(target)


def test_readonly_blocks_select():
    st = CalendarState(is_readonly=True)
    st.select_date(CalendarDate(2026, 7, 15))
    assert st.value is None


def test_disabled_blocks_select():
    st = CalendarState(is_disabled=True)
    st.select_date(CalendarDate(2026, 7, 15))
    assert st.value is None


def test_min_max_disable():
    st = CalendarState(min_value=CalendarDate(2026, 7, 10),
                       max_value=CalendarDate(2026, 7, 20))
    assert st.is_disabled_date(CalendarDate(2026, 7, 5))
    assert st.is_disabled_date(CalendarDate(2026, 7, 25))
    assert not st.is_disabled_date(CalendarDate(2026, 7, 15))
    st.select_date(CalendarDate(2026, 7, 5))  # 越界不可选
    assert st.value is None


def test_unavailable():
    weekend = lambda d: d.weekday in (1, 7)  # 周日/周六
    st = CalendarState(is_unavailable_fn=weekend)
    sat = CalendarDate(2026, 8, 1)  # 周六
    assert st.is_unavailable(sat)
    st.select_date(sat)
    assert st.value is None


def test_focus_change_signal():
    st = CalendarState(value=CalendarDate(2026, 7, 15))
    fired = []
    st.on_focus_change = fired.append
    st.set_focused_date(CalendarDate(2026, 7, 20))
    assert st.focused_date.is_same_day(CalendarDate(2026, 7, 20))
    assert len(fired) == 1


def test_paging_visible_vs_single():
    st_v = CalendarState(value=CalendarDate(2026, 7, 1), visible_months=2,
                         page_behavior="visible")
    st_v.focus_next_page()
    assert st_v.visible_range_start.month == 9  # 翻 2 个月

    st_s = CalendarState(value=CalendarDate(2026, 7, 1), visible_months=2,
                         page_behavior="single")
    st_s.focus_next_page()
    assert st_s.visible_range_start.month == 8  # 翻 1 个月


def test_visible_months_clamp():
    assert CalendarState(visible_months=5).visible_months == 3
    assert CalendarState(visible_months=0).visible_months == 1


def test_value_invalid():
    st = CalendarState(value=CalendarDate(2026, 7, 5),
                       min_value=CalendarDate(2026, 7, 10))
    assert st.is_value_invalid


# ---------------------------------------------------------------- _range

def test_range_two_click_select():
    st = RangeCalendarState()
    fired = []
    st.on_range_change = fired.append
    st.select_date(CalendarDate(2026, 7, 10))  # 第一次：锚点
    assert st.range_value is None
    assert st.anchor_date.is_same_day(CalendarDate(2026, 7, 10))
    st.select_date(CalendarDate(2026, 7, 20))  # 第二次：确定
    assert st.range_value is not None
    assert st.range_value[0].is_same_day(CalendarDate(2026, 7, 10))
    assert st.range_value[1].is_same_day(CalendarDate(2026, 7, 20))
    assert len(fired) == 1


def test_range_reverse_order_auto_sort():
    st = RangeCalendarState()
    st.select_date(CalendarDate(2026, 7, 20))
    st.select_date(CalendarDate(2026, 7, 10))  # 先大后小
    assert st.range_value[0].is_same_day(CalendarDate(2026, 7, 10))
    assert st.range_value[1].is_same_day(CalendarDate(2026, 7, 20))


def test_range_hover_preview():
    st = RangeCalendarState()
    st.select_date(CalendarDate(2026, 7, 10))  # 锚点
    st.set_hover_date(CalendarDate(2026, 7, 15))
    rng = st.highlighted_range()
    assert rng[0].is_same_day(CalendarDate(2026, 7, 10))
    assert rng[1].is_same_day(CalendarDate(2026, 7, 15))
    # 预览范围内的日期应被判为 selected
    assert st.is_selected(CalendarDate(2026, 7, 12))


def test_range_cell_state_endpoints():
    st = RangeCalendarState(value=(CalendarDate(2026, 7, 10),
                                   CalendarDate(2026, 7, 20)))
    today = CalendarDate.today()
    month = CalendarDate(2026, 7, 1)

    start_cell = compute_cell_state(CalendarDate(2026, 7, 10), month, st, today)
    mid_cell = compute_cell_state(CalendarDate(2026, 7, 15), month, st, today)
    end_cell = compute_cell_state(CalendarDate(2026, 7, 20), month, st, today)

    assert start_cell.is_selection_start and not start_cell.is_selection_end
    assert end_cell.is_selection_end and not end_cell.is_selection_start
    assert mid_cell.is_range_selection and not mid_cell.is_selection_start
    assert start_cell.is_range_selection and mid_cell.is_selected


def test_range_is_range_flag():
    assert RangeCalendarState().is_range() is True
    assert CalendarState().is_range() is False


# ---------------------------------------------------------------- picker 数据

def test_months_in_year():
    months = months_in_year()
    assert len(months) == 12
    assert months[0] == "January"
    assert months[6] == "July"


def test_year_range():
    yrs = year_range(CalendarDate(2020, 1, 1), CalendarDate(2025, 12, 31))
    assert yrs == [2020, 2021, 2022, 2023, 2024, 2025]
