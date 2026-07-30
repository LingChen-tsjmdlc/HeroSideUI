"""Avatar / AvatarGroup 组件测试"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QEnterEvent, QPixmap
from PySide6.QtTest import QTest

from hero_side_ui import Avatar, AvatarGroup, Text
from hero_side_ui.components.avatar import safe_initials

COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
RADII = ("none", "sm", "md", "lg", "full")
SIZES = ("sm", "md", "lg")


def _pixmap(w=64, h=64) -> QPixmap:
    pm = QPixmap(w, h)
    pm.fill()
    return pm


def _fake_enter_event(w) -> QEnterEvent:
    p = QPointF(w.width() / 2, w.height() / 2)
    return QEnterEvent(p, p, w.mapToGlobal(p.toPoint()))


def _fake_leave_event() -> QEvent:
    return QEvent(QEvent.Type.Leave)


class TestSafeInitials:
    def test_empty(self):
        assert safe_initials("") == ""
        assert safe_initials("   ") == ""

    def test_single_word(self):
        assert safe_initials("Junior") == "J"

    def test_two_words(self):
        assert safe_initials("Jane Wu") == "JW"

    def test_multi_words_first_last(self):
        assert safe_initials("John Ronald Tolkien") == "JT"

    def test_no_space_cjk(self):
        assert safe_initials("张伟") == "张"


class TestAvatarInit:
    def test_default_no_args(self, qtbot):
        a = Avatar()
        qtbot.addWidget(a)
        assert a._color == "default"
        assert a._radius == "full"
        assert a._size == "md"
        assert a._theme_mode == "auto"
        assert a._src is None

    def test_custom_params(self, qtbot):
        a = Avatar(name="Jane Wu", color="danger", radius="md", size="lg", theme="dark")
        qtbot.addWidget(a)
        assert a._name == "Jane Wu"
        assert a._color == "danger"
        assert a._radius == "md"
        assert a._size == "lg"
        assert a._theme == "dark"

    def test_invalid_size_falls_back_md(self, qtbot):
        a = Avatar(size="xxl")
        qtbot.addWidget(a)
        assert a._size == "md"

    def test_box_size_matches_token(self, qtbot):
        from hero_side_ui.themes import AVATAR_SIZES

        for s in SIZES:
            a = Avatar(size=s)
            qtbot.addWidget(a)
            side = AVATAR_SIZES[s]["box"]
            assert a.width() == side
            assert a.height() == side

    def test_bordered_adds_outer_margin(self, qtbot):
        from hero_side_ui.themes import (
            AVATAR_RING_OFFSET,
            AVATAR_RING_WIDTH,
            AVATAR_SIZES,
        )

        a = Avatar(size="md", is_bordered=True)
        qtbot.addWidget(a)
        side = AVATAR_SIZES["md"]["box"]
        extra = 2 * (AVATAR_RING_WIDTH + AVATAR_RING_OFFSET)
        assert a.width() == side + extra


class TestAvatarText:
    """文字唯一入口铁律：首字母标签必须是 Text 实例"""

    def test_name_label_is_text_component(self, qtbot):
        a = Avatar(name="JW")
        qtbot.addWidget(a)
        assert isinstance(a._name_label, Text)

    def test_initials_shown_when_no_src(self, qtbot):
        a = Avatar(name="Jane Wu")
        qtbot.addWidget(a)
        a.show()
        assert a._name_label.isVisible()
        assert a._name_label.text() == "JW"

    def test_icon_shown_when_no_name_no_src(self, qtbot):
        a = Avatar()
        qtbot.addWidget(a)
        a.show()
        assert a._icon_canvas.isVisible()
        assert not a._name_label.isVisible()


class TestAvatarColors:
    @pytest.mark.parametrize("color", COLORS)
    def test_all_colors_construct(self, qtbot, color):
        a = Avatar(name="X", color=color)
        qtbot.addWidget(a)
        assert a._color == color


class TestAvatarRadius:
    @pytest.mark.parametrize("radius", RADII)
    def test_all_radii_construct(self, qtbot, radius):
        a = Avatar(name="X", radius=radius)
        qtbot.addWidget(a)
        assert a._radius == radius


class TestAvatarSizes:
    @pytest.mark.parametrize("size", SIZES)
    def test_all_sizes_construct(self, qtbot, size):
        a = Avatar(name="X", size=size)
        qtbot.addWidget(a)
        assert a._size == size


class TestAvatarImage:
    def test_pixmap_src_loads(self, qtbot):
        a = Avatar(src=_pixmap())
        qtbot.addWidget(a)
        with qtbot.waitSignal(a.loaded, timeout=1000):
            pass
        assert a.status() == "loaded"
        assert a.pixmap() is not None

    def test_no_fallback_when_image_loaded(self, qtbot):
        a = Avatar(src=_pixmap(), name="JW")
        qtbot.addWidget(a)
        a.show()
        with qtbot.waitSignal(a.loaded, timeout=1000):
            pass
        # 加载成功后 name 首字母兜底隐藏
        assert not a._name_label.isVisible()

    def test_show_fallback_visible_before_load(self, qtbot):
        a = Avatar(src=_pixmap(), name="JW", show_fallback=True)
        qtbot.addWidget(a)
        a.show()
        # 构造后同步阶段 pixmap 还没通过 singleShot 发出 → 兜底应可见
        assert a._name_label.isVisible()


class TestAvatarDisabled:
    def test_disabled_flag(self, qtbot):
        a = Avatar(name="X", is_disabled=True)
        qtbot.addWidget(a)
        assert a._is_disabled
        assert not a.isEnabled()


class TestAvatarSetters:
    def test_set_name(self, qtbot):
        a = Avatar(name="Old Name")
        qtbot.addWidget(a)
        a.show()
        a.set_name("New Guy")
        assert a._name_label.text() == "NG"

    def test_set_color(self, qtbot):
        a = Avatar(name="X", color="default")
        qtbot.addWidget(a)
        a.set_color("success")
        assert a._color == "success"

    def test_set_size(self, qtbot):
        a = Avatar(name="X", size="sm")
        qtbot.addWidget(a)
        a.set_size("lg")
        assert a._size == "lg"

    def test_set_radius(self, qtbot):
        a = Avatar(name="X", radius="full")
        qtbot.addWidget(a)
        a.set_radius("none")
        assert a._radius == "none"

    def test_set_bordered(self, qtbot):
        a = Avatar(name="X")
        qtbot.addWidget(a)
        a.set_bordered(True)
        assert a._is_bordered

    def test_set_disabled(self, qtbot):
        a = Avatar(name="X")
        qtbot.addWidget(a)
        a.set_disabled(True)
        assert a._is_disabled
        assert not a.isEnabled()

    def test_set_src_switches_to_loading(self, qtbot):
        a = Avatar(name="X")
        qtbot.addWidget(a)
        a.set_src(_pixmap())
        with qtbot.waitSignal(a.loaded, timeout=1000):
            pass
        assert a.status() == "loaded"


class TestAvatarInteraction:
    """自定义点击 / hover 事件"""

    def test_pressable_sets_pointing_cursor(self, qtbot):
        a = Avatar(name="X", is_pressable=True)
        qtbot.addWidget(a)
        assert a.cursor().shape() == Qt.CursorShape.PointingHandCursor

    def test_disabled_sets_forbidden_cursor(self, qtbot):
        a = Avatar(name="X", is_pressable=True, is_disabled=True)
        qtbot.addWidget(a)
        assert a.cursor().shape() == Qt.CursorShape.ForbiddenCursor

    def test_click_signal(self, qtbot):
        a = Avatar(name="X", is_pressable=True)
        qtbot.addWidget(a)
        a.show()
        with qtbot.waitSignal(a.clicked, timeout=500):
            QTest.mouseClick(a, Qt.MouseButton.LeftButton)

    def test_press_release_signals(self, qtbot):
        a = Avatar(name="X", is_pressable=True)
        qtbot.addWidget(a)
        a.show()
        with qtbot.waitSignal(a.pressed, timeout=500):
            QTest.mousePress(a, Qt.MouseButton.LeftButton)
        with qtbot.waitSignal(a.released, timeout=500):
            QTest.mouseRelease(a, Qt.MouseButton.LeftButton)

    def test_on_click_callback(self, qtbot):
        calls = []
        a = Avatar(name="X", is_pressable=True, on_click=lambda: calls.append(1))
        qtbot.addWidget(a)
        a.show()
        QTest.mouseClick(a, Qt.MouseButton.LeftButton)
        assert calls == [1]

    def test_not_pressable_no_click(self, qtbot):
        calls = []
        a = Avatar(name="X", on_click=lambda: calls.append(1))
        qtbot.addWidget(a)
        a.show()
        QTest.mouseClick(a, Qt.MouseButton.LeftButton)
        assert calls == []

    def test_hover_signals(self, qtbot):
        a = Avatar(name="X")
        qtbot.addWidget(a)
        a.show()
        with qtbot.waitSignal(a.hovered, timeout=500):
            a.enterEvent(_fake_enter_event(a))

    def test_on_hover_callback(self, qtbot):
        states = []
        a = Avatar(name="X", on_hover=lambda h: states.append(h))
        qtbot.addWidget(a)
        a.show()
        a.enterEvent(_fake_enter_event(a))
        a.leaveEvent(_fake_leave_event())
        assert states == [True, False]

    def test_set_pressable(self, qtbot):
        a = Avatar(name="X")
        qtbot.addWidget(a)
        a.set_pressable(True)
        assert a._is_pressable
        assert a.cursor().shape() == Qt.CursorShape.PointingHandCursor


class TestAvatarTheme:
    def test_auto_follows_provider(self, qtbot):
        from hero_side_ui import ThemeProvider

        ThemeProvider._reset_for_test()
        p = ThemeProvider.instance()
        p.set_mode("light")
        a = Avatar(name="X")
        qtbot.addWidget(a)
        assert a._theme == "light"
        p.toggle()
        assert a._theme == "dark"
        ThemeProvider._reset_for_test()

    def test_fixed_theme_not_affected(self, qtbot):
        from hero_side_ui import ThemeProvider

        ThemeProvider._reset_for_test()
        p = ThemeProvider.instance()
        p.set_mode("light")
        a = Avatar(name="X", theme="dark")
        qtbot.addWidget(a)
        p.toggle()
        assert a._theme == "dark"
        ThemeProvider._reset_for_test()


class TestAvatarGroupInit:
    def test_default(self, qtbot):
        avs = [Avatar(name=str(i)) for i in range(3)]
        g = AvatarGroup(avs)
        qtbot.addWidget(g)
        assert g._max == 5
        assert len(g.avatars()) == 3

    def test_visible_capped_by_max(self, qtbot):
        avs = [Avatar(name=str(i)) for i in range(8)]
        g = AvatarGroup(avs, max=3)
        qtbot.addWidget(g)
        assert len(g._visible_avatars()) == 3

    def test_remaining_count_auto(self, qtbot):
        avs = [Avatar(name=str(i)) for i in range(8)]
        g = AvatarGroup(avs, max=3)
        qtbot.addWidget(g)
        assert g.remaining_count() == 5

    def test_stack_z_order_later_on_top(self, qtbot):
        # 越靠后的头像 z 越高 → raise_() 后它排在父 children 列表末尾（最顶）
        avs = [Avatar(name=str(i)) for i in range(4)]
        g = AvatarGroup(avs, max=4)
        qtbot.addWidget(g)
        g.show()
        item_children = [c for c in g.children() if c in g._items]
        # children() 顺序反映堆叠：最后 raise 的在末尾
        assert item_children[-1] is g._items[-1]

    def test_total_overrides_remaining(self, qtbot):
        avs = [Avatar(name=str(i)) for i in range(8)]
        g = AvatarGroup(avs, max=3, total=10)
        qtbot.addWidget(g)
        assert g.remaining_count() == 10

    def test_count_widget_created_when_overflow(self, qtbot):
        avs = [Avatar(name=str(i)) for i in range(8)]
        g = AvatarGroup(avs, max=3)
        qtbot.addWidget(g)
        assert g.count_widget() is not None

    def test_no_count_widget_within_max(self, qtbot):
        avs = [Avatar(name=str(i)) for i in range(3)]
        g = AvatarGroup(avs, max=5)
        qtbot.addWidget(g)
        assert g.count_widget() is None

    def test_props_propagate_to_children(self, qtbot):
        avs = [Avatar(name=str(i)) for i in range(3)]
        g = AvatarGroup(avs, color="primary", radius="sm", size="lg", is_bordered=True)
        qtbot.addWidget(g)
        for av in g._visible_avatars():
            assert av._color == "primary"
            assert av._radius == "sm"
            assert av._size == "lg"
            assert av._is_bordered

    def test_grid_mode_builds(self, qtbot):
        avs = [Avatar(name=str(i)) for i in range(9)]
        g = AvatarGroup(avs, max=7, is_grid=True)
        qtbot.addWidget(g)
        g.show()
        assert g._is_grid
        assert g.count_widget() is not None

    def test_custom_render_count(self, qtbot):
        made = []

        def _rc(n: int) -> Text:
            t = Text(f"+{n}")
            made.append(n)
            return t

        avs = [Avatar(name=str(i)) for i in range(8)]
        g = AvatarGroup(avs, max=3, total=10, render_count=_rc)
        qtbot.addWidget(g)
        assert made == [10]
        assert isinstance(g.count_widget(), Text)
