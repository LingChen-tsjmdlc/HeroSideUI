"""家族共享能力的公开接口，以及它们的真实消费者。"""

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

from hero_side_ui import (
    Autocomplete,
    Calendar,
    CalendarDate,
    DatePicker,
    DateRangePicker,
    Drawer,
    Dropdown,
    Input,
    Listbox,
    Popover,
    Select,
    parse_date,
)
from hero_side_ui._shared.dates import DateFieldState, DateTimeValue
from hero_side_ui._shared.overlays import Backdrop
from hero_side_ui._shared.selection import available_height_below, fit_popup_height


@pytest.fixture
def host(qtbot) -> QWidget:
    w = QWidget()
    qtbot.addWidget(w)
    w.resize(400, 300)
    return w


# ============================================================
# 浮层：Backdrop 与 Popover
# ============================================================
class TestBackdrop:
    def test_settle_jumps_to_final_progress(self, host):
        bd = Backdrop("opaque", host=host)
        bd.settle(1.0)
        assert bd._fade.progress_value() == 1.0
        bd.settle(0.0)
        assert bd._fade.progress_value() == 0.0

    def test_unknown_blur_quality_is_rejected(self, host):
        with pytest.raises(ValueError):
            Backdrop("blur", host=host, blur_quality="ultra")

    @pytest.mark.parametrize("quality", ["low", "fast", "great", "high"])
    def test_blur_snapshot_matches_host_size(self, host, quality):
        bd = Backdrop("blur", host=host, blur_quality=quality)
        bd.prepare_blur_snapshot()
        bd.refresh_blur_fast()
        assert bd._blur_pixmap is not None
        assert bd._blur_pixmap.size() == host.grab().size()

    def test_drawer_and_popover_share_the_same_class(self, host):
        from hero_side_ui.components.popover import popover as popover_module

        d = Drawer(host=host, backdrop="opaque", disable_animation=True)
        d.set_is_open(True)
        assert type(d._backdrop) is Backdrop
        assert popover_module.Backdrop is Backdrop


class TestPopoverPublicApi:
    def test_frame_margins_are_exposed(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        assert p.frame_margins() == p._frame_margins()

    def test_fade_durations_can_be_tuned(self, qtbot):
        p = Popover()
        qtbot.addWidget(p)
        p.set_fade_durations(140, 100)
        assert (p._fade._duration_in, p._fade._duration_out) == (140, 100)

    @pytest.mark.parametrize("factory", [Select, Autocomplete, Dropdown])
    def test_popup_components_tune_fade_through_the_public_api(self, qtbot, factory):
        w = factory()
        qtbot.addWidget(w)
        assert (w._popover._fade._duration_in, w._popover._fade._duration_out) == (140, 100)


# ============================================================
# 列表：Listbox 导航与高度
# ============================================================
def _listbox(qtbot) -> Listbox:
    lb = Listbox(selection_mode="single")
    qtbot.addWidget(lb)
    lb.add_item("A", key="a")
    lb.add_item("B", key="b", is_disabled=True)
    lb.add_item("C", key="c")
    return lb


class TestListboxPublicApi:
    def test_enabled_bounds_skip_disabled_items(self, qtbot):
        lb = _listbox(qtbot)
        assert lb.first_enabled_index() == 0
        assert lb.last_enabled_index() == 2

    def test_focus_moves_over_enabled_items_and_wraps(self, qtbot):
        lb = _listbox(qtbot)
        assert lb.focused_index() == -1
        lb.move_focus(1)
        assert lb.focused_index() == 0
        lb.move_focus(1)
        assert lb.focused_index() == 2
        lb.move_focus(1)
        assert lb.focused_index() == 0
        lb.set_focus_index(2)
        assert lb.focused_index() == 2

    def test_activate_focused_selects_the_item(self, qtbot):
        lb = _listbox(qtbot)
        assert lb.activate_focused() is False
        lb.set_focus_index(2)
        assert lb.activate_focused() is True
        assert lb.selected_keys() == {"c"}

    def test_activate_focused_ignores_disabled_items(self, qtbot):
        lb = _listbox(qtbot)
        lb.set_focus_index(1)
        assert lb.activate_focused() is False
        assert lb.selected_keys() == set()

    def test_empty_placeholder_visibility_is_controllable(self, qtbot):
        lb = _listbox(qtbot)
        lb.set_empty_visible(True)
        assert not lb._empty_widget.isHidden()
        lb.set_empty_visible(False)
        assert lb._empty_widget.isHidden()

    def test_content_height_follows_visible_items(self, qtbot):
        lb = _listbox(qtbot)
        full = lb.visible_content_height()
        for it in lb.items()[1:]:
            it.setVisible(False)
        assert 0 < lb.visible_content_height() < full


class TestPopupHeight:
    def _make(self, qtbot, count):
        lb = Listbox()
        qtbot.addWidget(lb)
        for i in range(count):
            lb.add_item(f"Item {i}", key=str(i))
        return QScrollArea(), lb

    def test_short_list_shrinks_to_content(self, qtbot):
        scroll, lb = self._make(qtbot, 1)
        fit_popup_height(scroll, lb, token_max=260)
        assert scroll.minimumHeight() < 260
        assert scroll.maximumHeight() == 260

    def test_long_list_uses_the_token_cap(self, qtbot):
        scroll, lb = self._make(qtbot, 40)
        fit_popup_height(scroll, lb, token_max=260)
        assert scroll.minimumHeight() == scroll.maximumHeight() == 260

    def test_available_space_lowers_the_cap_but_not_below_the_minimum(self, qtbot):
        scroll, lb = self._make(qtbot, 40)
        fit_popup_height(scroll, lb, token_max=260, available=150)
        assert scroll.maximumHeight() == 150
        fit_popup_height(scroll, lb, token_max=260, available=10)
        assert scroll.maximumHeight() == 80

    @pytest.mark.parametrize("factory", [Select, Autocomplete])
    def test_consumers_use_the_shared_calculation(self, qtbot, factory):
        w = factory(items=[(str(i), f"Item {i}") for i in range(40)])
        qtbot.addWidget(w)
        w._refresh_popover_height()
        assert w._scroll.maximumHeight() == w._popover_max_height()

    def test_available_height_subtracts_gap_and_popover_margin(self, qtbot):
        anchor = QWidget()
        qtbot.addWidget(anchor)
        anchor.resize(100, 30)
        p = Popover()
        qtbot.addWidget(p)
        bottom = QApplication.primaryScreen().availableGeometry().bottom()
        below = anchor.mapToGlobal(QPoint(0, 0)).y() + anchor.height()
        expected = bottom - below - 6 - p.frame_margins()[3]
        assert available_height_below(anchor, p, fallback=0) == expected


# ============================================================
# 输入：Input 公开接口
# ============================================================
class TestInputPublicApi:
    def test_readonly_reflects_the_setter(self, qtbot):
        i = Input()
        qtbot.addWidget(i)
        assert i.is_readonly() is False
        i.set_is_readonly(True)
        assert i.is_readonly() is True

    def test_click_targets_cover_the_whole_field(self, qtbot):
        i = Input(label="x")
        qtbot.addWidget(i)
        assert i.click_targets() == (i.line_edit, i._wrapper, i._inside_label)

    def test_refresh_filled_state_floats_the_label(self, qtbot):
        i = Input(label="x")
        qtbot.addWidget(i)
        i.line_edit.blockSignals(True)
        i.line_edit.setText("typed")
        i.line_edit.blockSignals(False)
        i.refresh_filled_state(animate=False)
        assert i._label_anim.progress_value() == 1.0


# ============================================================
# 日期：共享模型与兼容入口
# ============================================================
class TestDateModel:
    def test_field_state_exposes_its_configuration(self):
        lo, hi = parse_date("2020-01-01"), parse_date("2030-01-01")
        st = DateFieldState(min_value=lo, max_value=hi, should_force_leading_zeros=False)
        assert (st.min_value, st.max_value, st.force_zeros) == (lo, hi, False)
        assert isinstance(st.placeholder, DateTimeValue)
        st.max_value = None
        assert st.max_value is None

    def test_set_segment_is_public(self):
        st = DateFieldState(value=parse_date("2024-05-10"))
        st.set_segment("month", 2)
        assert st.value().date.month == 2

    def test_legacy_import_paths_resolve_to_the_same_objects(self):
        from hero_side_ui import parse_datetime
        from hero_side_ui.components.calendar._date import CalendarDate as LegacyDate
        from hero_side_ui.components.date_input._value import parse_datetime as legacy_parse

        assert LegacyDate is CalendarDate
        assert legacy_parse is parse_datetime


class TestCalendarSurface:
    @pytest.mark.parametrize("theme,color", [("light", "#ffffff"), ("dark", "#27272a")])
    def test_popover_surface_matches_the_popover_background(self, qtbot, theme, color):
        c = Calendar(surface="popover", theme=theme)
        qtbot.addWidget(c)
        assert f"background: {color}" in c.styleSheet()

    def test_surface_can_be_switched_and_validated(self, qtbot):
        c = Calendar(theme="light")
        qtbot.addWidget(c)
        default_style = c.styleSheet()
        c.set_surface("popover")
        assert c.styleSheet() != default_style
        c.set_surface("default")
        assert c.styleSheet() == default_style
        with pytest.raises(ValueError):
            c.set_surface("card")
        with pytest.raises(ValueError):
            Calendar(surface="card")

    def test_pickers_embed_a_plain_calendar_with_the_popover_surface(self, qtbot):
        single, ranged = DatePicker(), DateRangePicker()
        qtbot.addWidget(single)
        qtbot.addWidget(ranged)
        assert type(single._calendar) is Calendar
        assert type(ranged._calendar).__name__ == "RangeCalendar"
        assert single._calendar._surface == ranged._calendar._surface == "popover"
