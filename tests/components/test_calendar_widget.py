"""Calendar 渲染层测试（P2：Calendar 单选组件）。

构造/参数遍历/信号/API，走 pytest-qt。纯日期逻辑见 test_calendar_logic.py。
"""

import pytest

from hero_side_ui import Calendar
from hero_side_ui.components.calendar._date import CalendarDate


def _make(qtbot, **kwargs) -> Calendar:
    c = Calendar(**kwargs)
    qtbot.addWidget(c)
    return c


def test_construct_default(qtbot):
    c = _make(qtbot)
    assert c.value() is None


def test_construct_all_colors(qtbot):
    for color in ("foreground", "primary", "secondary", "success", "warning", "danger"):
        c = _make(qtbot, color=color)
        assert c is not None


def test_invalid_color_falls_back(qtbot):
    c = _make(qtbot, color="nope")
    assert c._color == "primary"


def test_preset_value(qtbot):
    v = CalendarDate(2026, 7, 15)
    c = _make(qtbot, value=v)
    assert c.value().is_same_day(v)


def test_change_signal_on_select(qtbot):
    c = _make(qtbot)
    received = []
    c.change.connect(received.append)
    c._on_date_clicked(CalendarDate(2026, 7, 10))
    assert len(received) == 1
    assert received[0].is_same_day(CalendarDate(2026, 7, 10))
    assert c.value().is_same_day(CalendarDate(2026, 7, 10))


def test_paging_changes_title(qtbot):
    c = _make(qtbot, value=CalendarDate(2026, 7, 15))
    before = c._header._titles[0].text()
    c._on_next()
    after = c._header._titles[0].text()
    assert before != after


def test_readonly_blocks_select(qtbot):
    c = _make(qtbot, value=CalendarDate(2026, 7, 15), is_readonly=True)
    c._on_date_clicked(CalendarDate(2026, 7, 20))
    assert c.value().is_same_day(CalendarDate(2026, 7, 15))  # 未变


def test_set_color_runtime(qtbot):
    c = _make(qtbot)
    c.set_color("danger")
    assert c._color == "danger"


def test_theme_switch(qtbot):
    c = _make(qtbot, theme="light")
    c.set_theme("dark")
    assert c._theme == "dark"


def test_first_day_of_week(qtbot):
    c = _make(qtbot, first_day_of_week="mon", weekday_style="short")
    labels = [lbl.text() for lbl in c._weekday_bar._labels[:7]]
    assert labels[0] == "Mon"


def test_min_max_disables_paging(qtbot):
    v = CalendarDate(2026, 7, 15)
    c = _make(qtbot, value=v, min_value=v.first_of_month(),
              max_value=v.last_of_month())
    assert not c._header._prev_btn.isEnabled()
    assert not c._header._next_btn.isEnabled()


def test_visible_months_multi(qtbot):
    c = _make(qtbot, visible_months=3)
    assert len(c._months) == 3
    assert len(c._header._titles) == 3


def test_visible_months_clamped(qtbot):
    c = _make(qtbot, visible_months=5)
    assert len(c._months) == 3  # clamp 到 3


def test_multi_month_titles(qtbot):
    c = _make(qtbot, value=CalendarDate(2026, 7, 1), visible_months=2)
    titles = [t.text() for t in c._header._titles]
    assert titles[0] != titles[1]  # 两个月标题不同


def test_disable_animation_pages(qtbot):
    c = _make(qtbot, value=CalendarDate(2026, 7, 15), disable_animation=True)
    before = c._header._titles[0].text()
    c._on_next()
    assert c._header._titles[0].text() != before


# ---- P4 月/年选择器 ----

def test_pickers_off_by_default(qtbot):
    c = _make(qtbot)
    assert c._show_pickers is False
    assert c._picker is None


def test_pickers_enabled(qtbot):
    c = _make(qtbot, show_month_and_year_pickers=True)
    assert c._show_pickers is True
    assert c._picker is not None


def test_pickers_disabled_when_multi_month(qtbot):
    c = _make(qtbot, show_month_and_year_pickers=True, visible_months=2)
    assert c._show_pickers is False  # 仅单月生效


def test_header_expand_toggle_and_signal(qtbot):
    c = _make(qtbot, show_month_and_year_pickers=True,
              value=CalendarDate(2026, 7, 15))
    received = []
    c.header_expanded_change.connect(received.append)
    assert c.is_header_expanded() is False
    c.set_header_expanded(True)
    assert c.is_header_expanded() is True
    assert received == [True]
    c.set_header_expanded(False)
    assert c.is_header_expanded() is False
    assert received == [True, False]


def test_default_expanded(qtbot):
    c = _make(qtbot, show_month_and_year_pickers=True,
              is_header_default_expanded=True)
    assert c.is_header_expanded() is True


def test_picker_month_change_updates_focus(qtbot):
    c = _make(qtbot, show_month_and_year_pickers=True,
              value=CalendarDate(2026, 7, 15))
    c._on_picker_month(10)
    assert c._state.focused_date.month == 10


def test_picker_year_change_updates_focus(qtbot):
    c = _make(qtbot, show_month_and_year_pickers=True,
              value=CalendarDate(2026, 7, 15))
    c._on_picker_year(2030)
    assert c._state.focused_date.year == 2030


# ---- P6 invalid / error / focus ----

def test_invalid_shows_error_message(qtbot):
    c = _make(qtbot, value=CalendarDate(2026, 7, 15), is_invalid=True,
              error_message="bad date")
    assert c._error_label.text() == "bad date"
    assert c.is_invalid() is True


def test_error_label_hidden_when_valid(qtbot):
    # 错误标签总是创建（支持运行时 set_invalid），valid 时隐藏、无文本
    c = _make(qtbot, value=CalendarDate(2026, 7, 15))
    assert c.is_invalid() is False
    assert c._error_label.text() == ""


def test_set_invalid_runtime(qtbot):
    c = _make(qtbot, value=CalendarDate(2026, 7, 15))
    c.set_invalid(True, "选到休息日了")
    assert c.is_invalid() is True
    assert c._error_label.text() == "选到休息日了"
    c.set_invalid(False)
    assert c.is_invalid() is False


def test_focus_change_signal_on_paging(qtbot):
    c = _make(qtbot, value=CalendarDate(2026, 7, 15))
    received = []
    c.focus_change.connect(received.append)
    c._on_next()
    assert len(received) >= 1



