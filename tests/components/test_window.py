"""Window 单元测试：配置继承、槽、尺寸限制、风格布局、命中测试。"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLineEdit, QPushButton, QWidget

from hero_side_ui import ThemeProvider, Window
from hero_side_ui.components.window import _native
from hero_side_ui.components.window._style import (
    button_size,
    controls_width,
    mac_diameter,
    min_size_floor,
)

SYSTEMS = ("windows", "mac", "linux")
STANDARD_HEIGHT = {"windows": 32, "mac": 28, "linux": 40}


def _make(qtbot, **kw) -> Window:
    w = Window(**kw)
    qtbot.addWidget(w)
    return w


def _shown(qtbot, **kw) -> Window:
    kw.setdefault("width", 900)
    kw.setdefault("height", 500)
    w = _make(qtbot, **kw)
    w.show()
    qtbot.wait(30)
    return w


class TestConstruct:
    def test_defaults(self, qtbot):
        w = _make(qtbot)
        assert w.system() is None and w.title_bar_height() is None
        assert w.radius() == "system" and not w._beta
        assert w.resolved_controls() == (True, True, True)
        assert w.resolved_resizable() is True
        assert (w.width(), w.height()) == (800, 600)

    @pytest.mark.parametrize("system", SYSTEMS)
    def test_standard_title_bar_height(self, qtbot, system):
        w = _make(qtbot, system=system)
        assert w.resolved_system() == system
        assert w.resolved_title_bar_height() == STANDARD_HEIGHT[system]

    def test_auto_resolves_to_a_real_system(self, qtbot):
        assert _make(qtbot, system="auto").resolved_system() in SYSTEMS

    @pytest.mark.parametrize(
        "kw",
        [
            {"system": "ios"},
            {"radius": "xl"},
            {"radius": "none"},
            {"radius": True},
            {"radius": -1},
            {"radius": float("nan")},
            {"radius": float("inf")},
            {"title_bar_height": True},
            {"title_bar_height": 0},
            {"show_close": "yes"},
            {"resizable": 1},
            {"theme": "red"},
            {"width": 0},
        ],
    )
    def test_invalid_arguments_raise(self, qtbot, kw):
        with pytest.raises(ValueError):
            Window(**kw)

    def test_initial_size_clamped_into_limits(self, qtbot):
        w = _make(qtbot, width=100, height=50)
        assert (w.width(), w.height()) == (w.minimumWidth(), w.minimumHeight())
        w2 = _make(qtbot, width=2000, height=2000, max_width=900, max_height=700)
        assert (w2.width(), w2.height()) == (900, 700)


class TestSetters:
    def test_title_bar_height_clamped_to_minimum(self, qtbot):
        w = _make(qtbot, system="windows")
        w.set_title_bar_height(5)
        assert w.resolved_title_bar_height() == 20
        w.set_title_bar_height(48)
        assert w.resolved_title_bar_height() == 48
        w.set_title_bar_height(None)
        assert w.resolved_title_bar_height() == 32

    def test_title_bar_height_resizes_the_bar(self, qtbot):
        w = _make(qtbot, system="windows")
        w.set_title_bar_height(44)
        assert w._title_bar.maximumHeight() == 44

    def test_system_switch_updates_standard_height_and_emits(self, qtbot):
        w = _make(qtbot, system="windows")
        with qtbot.waitSignal(w.system_changed, timeout=500) as sig:
            w.set_system("linux")
        assert sig.args == ["linux"]
        assert w.resolved_title_bar_height() == 40

    def test_set_controls_leaves_unspecified_untouched(self, qtbot):
        w = _make(qtbot)
        w.set_controls(minimize=False)
        assert w.resolved_controls() == (False, True, True)
        w.set_controls(close=False)
        assert w.resolved_controls() == (False, True, False)
        w.set_controls(minimize=None, close=None)
        assert w.resolved_controls() == (True, True, True)

    def test_hidden_control_is_hidden_in_title_bar(self, qtbot):
        w = _make(qtbot)
        w.set_controls(close=False)
        assert w._title_bar.controls().button("close").isHidden()

    @pytest.mark.parametrize(
        "setter,value",
        [("set_system", "ios"), ("set_radius", "xl"), ("set_resizable", "no")],
    )
    def test_invalid_setter_raises(self, qtbot, setter, value):
        w = _make(qtbot)
        with pytest.raises(ValueError):
            getattr(w, setter)(value)

    def test_resizable_false_hides_maximize(self, qtbot):
        w = _make(qtbot)
        w.set_resizable(False)
        assert w._title_bar.controls().button("maximize").isHidden()
        w.set_resizable(None)
        assert not w._title_bar.controls().button("maximize").isHidden()


class TestInheritance:
    def test_child_inherits_and_follows_parent(self, qtbot):
        main = _make(qtbot, system="windows", title_bar_height=36, radius="lg")
        child = Window(parent=main)
        assert child.resolved_system() == "windows"
        assert child.resolved_title_bar_height() == 36
        main.set_title_bar_height(30)
        assert child.resolved_title_bar_height() == 30
        assert child._title_bar.maximumHeight() == 30

    def test_radius_is_not_inherited(self, qtbot):
        main = _make(qtbot, radius="lg")
        child = Window(parent=main)
        assert child.radius() == "system" and not child._beta
        assert main._beta

    def test_own_value_overrides_and_none_restores(self, qtbot):
        main = _make(qtbot, system="windows", title_bar_height=36)
        child = Window(parent=main, system="mac")
        assert child.resolved_system() == "mac"
        assert child.resolved_title_bar_height() == 36
        child.set_title_bar_height(40)
        main.set_title_bar_height(34)
        assert child.resolved_title_bar_height() == 40
        child.set_title_bar_height(None)
        assert child.resolved_title_bar_height() == 34

    def test_controls_are_inherited(self, qtbot):
        main = _make(qtbot, show_maximize=False)
        child = Window(parent=main)
        assert child.resolved_controls() == (True, False, True)
        assert child._title_bar.controls().button("maximize").isHidden()
        child.set_controls(maximize=True)
        assert not child._title_bar.controls().button("maximize").isHidden()

    def test_grandchild_follows_through_chain(self, qtbot):
        main = _make(qtbot, system="linux")
        mid = Window(parent=main)
        leaf = Window(parent=mid)
        assert leaf.resolved_system() == "linux"
        main.set_system("mac")
        assert leaf.resolved_system() == "mac"

    def test_size_is_not_inherited(self, qtbot):
        main = _make(qtbot, width=1000, height=700)
        child = Window(parent=main)
        assert (child.width(), child.height()) == (800, 600)

    def test_no_window_ancestor_falls_back_to_defaults(self, qtbot):
        holder = QWidget()
        qtbot.addWidget(holder)
        w = Window(parent=holder)
        assert w.resolved_controls() == (True, True, True)

    def test_closing_parent_closes_visible_children(self, qtbot):
        main = _shown(qtbot)
        child = Window(parent=main, width=400, height=300)
        child.show()
        qtbot.wait(30)
        main.close()
        assert not child.isVisible()


class TestSizeLimits:
    def test_floor_applies_when_min_not_given(self, qtbot):
        w = _make(qtbot)
        assert w.minimumWidth() >= 280 and w.minimumHeight() >= 160

    def test_user_min_below_floor_is_lifted_above_floor_is_kept(self, qtbot):
        w = _make(qtbot)
        w.setMinimumSize(100, 100)
        assert w.minimumWidth() >= 280
        w.setMinimumSize(500, 400)
        assert (w.minimumWidth(), w.minimumHeight()) == (500, 400)

    def test_floor_follows_title_bar_height(self, qtbot):
        w = _make(qtbot, system="windows")
        w.set_title_bar_height(200)
        assert w.minimumHeight() >= 200 + 40

    def test_finite_max_keeps_maximize_button(self, qtbot):
        w = _make(qtbot)
        w.setMaximumSize(1000, 700)
        assert not w._title_bar.controls().button("maximize").isHidden()
        assert w._can_maximize()

    def test_fixed_size_hides_maximize(self, qtbot):
        w = _make(qtbot)
        w.setFixedSize(500, 400)
        assert w._title_bar.controls().button("maximize").isHidden()
        assert (w.width(), w.height()) == (500, 400)

    def test_releasing_fixed_size_restores_maximize(self, qtbot):
        w = _make(qtbot)
        w.setFixedSize(500, 400)
        w.setMinimumSize(0, 0)
        w.setMaximumSize(16777215, 16777215)
        assert not w._title_bar.controls().button("maximize").isHidden()


class TestMaximizeTarget:
    """设了最大尺寸后的最大化：逐方向取 min(工作区, 最大尺寸)，居中；都不小于工作区则真最大化。"""

    @staticmethod
    def _avail(w: Window):
        return w.screen().availableGeometry()

    def test_unlimited_is_real_maximize(self, qtbot):
        assert _make(qtbot)._maximize_target() is None

    def test_max_not_smaller_than_screen_is_real_maximize(self, qtbot):
        w = _make(qtbot)
        a = self._avail(w)
        w.setMaximumSize(a.width() + 500, a.height())
        assert w._maximize_target() is None

    def test_both_smaller_clamps_and_centers(self, qtbot):
        w = _make(qtbot)
        a = self._avail(w)
        mw, mh = a.width() - 200, a.height() - 100
        w.setMaximumSize(mw, mh)
        t = w._maximize_target()
        assert (t.width(), t.height()) == (mw, mh)
        assert t.center().x() - a.center().x() in (-1, 0, 1)
        assert t.center().y() - a.center().y() in (-1, 0, 1)

    def test_one_side_smaller_other_side_fills_screen(self, qtbot):
        w = _make(qtbot)
        a = self._avail(w)
        w.setMaximumSize(a.width() + 800, a.height() - 120)
        t = w._maximize_target()
        assert t.width() == a.width()
        assert t.height() == a.height() - 120
        assert t.x() == a.x()
        w.setMaximumSize(a.width() - 150, a.height() + 800)
        t = w._maximize_target()
        assert t.width() == a.width() - 150 and t.height() == a.height()
        assert t.y() == a.y()

    def test_soft_maximize_moves_window_and_restore_goes_back(self, qtbot):
        w = _shown(qtbot, width=400, height=300)
        w.move(20, 30)
        before = w.geometry()
        a = self._avail(w)
        w.setMaximumSize(a.width() - 200, a.height() - 100)
        with qtbot.waitSignal(w.maximized_changed, timeout=500) as sig:
            w.showMaximized()
        assert sig.args == [True]
        assert w.isMaximized() and w._soft_max
        assert w.geometry() == w._maximize_target()
        assert not w._is_expanded()
        with qtbot.waitSignal(w.maximized_changed, timeout=500) as sig:
            w.showNormal()
        assert sig.args == [False]
        assert not w.isMaximized()
        assert w.geometry() == before

    def test_moving_away_ends_soft_maximize(self, qtbot):
        w = _shown(qtbot, width=400, height=300)
        a = self._avail(w)
        w.setMaximumSize(a.width() - 200, a.height() - 100)
        w.showMaximized()
        w.move(w.x() + 5, w.y() + 5)
        assert not w.isMaximized()


class TestSlots:
    def test_default_title_goes_left_on_windows_center_on_mac(self, qtbot):
        w = _make(qtbot, system="windows")
        bar = w._title_bar
        assert bar.slot("left").content() is w._default_title
        w.set_system("mac")
        assert bar.slot("center").content() is w._default_title
        assert bar.slot("left").content() is None
        w.set_system("windows")
        assert bar.slot("left").content() is w._default_title
        assert bar.slot("center").content() is None

    def test_custom_widget_replaces_default_and_none_restores(self, qtbot):
        w = _make(qtbot, system="windows")
        left = w._title_bar.slot("left")
        edit = QLineEdit()
        w.set_left(edit)
        assert left.content() is edit
        w.set_left(None)
        assert left.content() is w._default_title

    def test_other_slots_do_not_disturb_default_title(self, qtbot):
        w = _make(qtbot, system="windows")
        btn = QPushButton("x")
        w.set_center(btn)
        assert w._title_bar.slot("center").content() is btn
        assert w._title_bar.slot("left").content() is w._default_title

    def test_default_title_follows_window_title(self, qtbot):
        w = _make(qtbot)
        w.setWindowTitle("Hello")
        assert w._default_title._title == "Hello"
        extra = w.default_title_widget()
        w.setWindowTitle("Again")
        assert extra._title == "Again"


class TestLayout:
    @pytest.mark.parametrize("system", ("windows", "linux"))
    def test_controls_at_right_edge(self, qtbot, system):
        w = _shown(qtbot, system=system)
        controls = w._title_bar.controls().geometry()
        assert controls.right() + 1 == w._title_bar.width()

    def test_flexible_slots_split_evenly_on_windows(self, qtbot):
        w = _shown(qtbot, system="windows")
        center = w._title_bar.slot("center").width()
        right = w._title_bar.slot("right").width()
        assert abs(center - right) <= 1

    def test_mac_controls_left_and_center_slot_centered(self, qtbot):
        w = _shown(qtbot, system="mac")
        bar = w._title_bar
        assert bar.controls().x() == 0
        center = bar.slot("center").geometry()
        assert abs(center.x() + center.width() / 2 - bar.width() / 2) <= 1

    def test_mac_flexible_slots_are_symmetric(self, qtbot):
        w = _shown(qtbot, system="mac")
        bar = w._title_bar
        left, right = bar.slot("left").width(), bar.slot("right").width()
        assert abs(left - right) <= 1

    def test_mac_button_order_is_close_minimize_zoom(self, qtbot):
        w = _shown(qtbot, system="mac")
        c = w._title_bar.controls()
        xs = [c.button(k).x() for k in ("close", "minimize", "maximize")]
        assert xs == sorted(xs)

    def test_expanding_widget_fills_flexible_slot(self, qtbot):
        w = _make(qtbot, system="windows", width=900, height=500)
        edit = QLineEdit()
        w.set_center(edit)
        w.show()
        qtbot.wait(30)
        assert edit.width() >= w._title_bar.slot("center").width() - 1


class TestRadiusModes:
    """radius 决定模式：system / None / 0 是系统模式（不透明），档位名或正数是自绘模式（beta，透明）。"""

    @pytest.mark.parametrize("value", ["system", None, 0, 0.0])
    def test_system_modes_are_opaque(self, qtbot, value):
        from PySide6.QtCore import Qt

        w = _make(qtbot, radius=value)
        assert not w._beta
        assert not w.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert w._radius_px() == 0

    @pytest.mark.parametrize("value,px", [("sm", 6), ("md", 10), ("lg", 14), (20, 20), (7.5, 7.5)])
    def test_custom_modes_are_translucent(self, qtbot, value, px):
        from PySide6.QtCore import Qt

        w = _make(qtbot, radius=value)
        assert w._beta
        assert w.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert w._radius_px() == px

    def test_system_mode_cannot_switch_to_custom(self, qtbot):
        w = _make(qtbot)
        for value in ("md", 12):
            with pytest.raises(ValueError):
                w.set_radius(value)
        assert w.radius() == "system"

    def test_custom_mode_cannot_switch_to_system(self, qtbot):
        w = _make(qtbot, radius="md")
        with pytest.raises(ValueError):
            w.set_radius("system")
        assert w.radius() == "md"

    def test_switching_inside_system_mode(self, qtbot):
        w = _make(qtbot)
        w.set_radius(None)
        assert w._system_square() and w.radius() is None
        w.set_radius("system")
        assert not w._system_square()

    def test_switching_inside_custom_mode(self, qtbot):
        w = _make(qtbot, radius="md")
        w.set_radius("lg")
        assert w._radius_px() == 14
        w.set_radius(30)
        assert w._radius_px() == 30
        w.set_radius(0)
        assert w._beta and w._radius_px() == 0

    def test_custom_radius_zero_when_expanded(self, qtbot):
        w = _make(qtbot, radius="lg")
        w.showFullScreen()
        assert w._radius_px() == 0


class TestRoundedPath:
    def test_bounds_match_rect_for_any_smoothing(self):
        from PySide6.QtCore import QRectF

        from hero_side_ui.components.window._frame import rounded_path

        rect = QRectF(0, 0, 400, 300)
        for s in (0.0, 0.6, 1.0):
            b = rounded_path(rect, 12, s).boundingRect()
            assert (round(b.x()), round(b.y()), b.width(), b.height()) == (0, 0, 400, 300)

    def test_zero_radius_is_plain_rect(self):
        from PySide6.QtCore import QRectF

        from hero_side_ui.components.window._frame import rounded_path

        assert rounded_path(QRectF(0, 0, 100, 80), 0).boundingRect().getRect() == (0, 0, 100, 80)

    def test_tiny_window_clamps_instead_of_crossing(self):
        from PySide6.QtCore import QRectF

        from hero_side_ui.components.window._frame import rounded_path

        b = rounded_path(QRectF(0, 0, 30, 20), 18, 0.6).boundingRect()
        assert b.width() == 30 and b.height() == 20

    def test_corner_is_cut_away(self):
        from PySide6.QtCore import QPointF, QRectF

        from hero_side_ui.components.window._frame import rounded_path

        path = rounded_path(QRectF(0, 0, 200, 200), 18, 0.6)
        assert not path.contains(QPointF(1, 1))
        assert path.contains(QPointF(100, 100))


class TestStyleHelpers:
    def test_button_sizes_follow_title_bar_height(self):
        assert button_size("windows", 32) == (46, 32)
        assert button_size("windows", 48) == (46, 48)
        assert button_size("linux", 40) == (24, 24)
        assert button_size("linux", 20) == (16, 16)
        assert mac_diameter(28) == 16
        assert mac_diameter(56) == 32

    def test_controls_width_and_floor(self):
        assert controls_width("windows", 32, 3) == 138
        assert controls_width("windows", 32, 0) == 0
        assert min_size_floor("windows", 32, 3) == (280, 160)
        assert min_size_floor("windows", 300, 3) == (280, 340)


class TestHitTest:
    def test_edges_corners_caption_and_client(self, qtbot):
        w = _shown(qtbot, system="windows")
        assert w._hit_test(QPoint(2, 250)) == _native.HTLEFT
        assert w._hit_test(QPoint(2, 2)) == _native.HTTOPLEFT
        assert w._hit_test(QPoint(897, 497)) == _native.HTBOTTOMRIGHT
        assert w._hit_test(QPoint(450, 16)) == _native.HTCAPTION
        assert w._hit_test(QPoint(450, 300)) == _native.HTCLIENT

    def test_maximize_button_and_client_buttons(self, qtbot):
        w = _shown(qtbot, system="windows")
        c = w._title_bar.controls()
        mx = c.button_rect("maximize").translated(c.pos())
        cl = c.button_rect("close").translated(c.pos())
        assert w._hit_test(mx.center()) == _native.HTMAXBUTTON
        assert w._hit_test(cl.center()) == _native.HTCLIENT

    def test_mac_has_no_max_button_hit(self, qtbot):
        w = _shown(qtbot, system="mac")
        c = w._title_bar.controls()
        mx = c.button_rect("maximize").translated(c.pos())
        assert w._hit_test(mx.center()) == _native.HTCLIENT

    def test_not_resizable_has_no_edges(self, qtbot):
        w = _shown(qtbot, system="windows", resizable=False)
        assert w._hit_test(QPoint(2, 250)) == _native.HTCLIENT

    def test_interactive_slot_widget_is_client_not_caption(self, qtbot):
        w = _make(qtbot, system="windows", width=900, height=500)
        edit = QLineEdit()
        w.set_center(edit)
        w.show()
        qtbot.wait(30)
        pos = edit.mapTo(w, edit.rect().center())
        assert w._hit_test(pos) == _native.HTCLIENT


class TestTheme:
    @pytest.fixture
    def provider(self):
        ThemeProvider._reset_for_test()
        p = ThemeProvider.instance()
        p.set_mode("light")
        yield p
        ThemeProvider._reset_for_test()

    def test_fixed_theme_ignores_global_toggle(self, qtbot, provider):
        w = _make(qtbot, theme="dark")
        provider.toggle()
        assert w._theme == "dark"

    def test_auto_follows_global_toggle(self, qtbot, provider):
        w = _make(qtbot, theme="auto")
        assert w._theme == "light"
        provider.toggle()
        assert w._theme == "dark"

    def test_set_theme_changes_colors(self, qtbot, provider):
        w = _make(qtbot, theme="light")
        light_bg = w._colors.background.name()
        w.set_theme("dark")
        assert w._colors.background.name() != light_bg
        with pytest.raises(ValueError):
            w.set_theme("red")
