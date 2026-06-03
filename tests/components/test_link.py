"""Link 组件单元测试。

覆盖维度：构造默认值、参数校验、setter、size/color/underline/isBlock/
isExternal/isDisabled/showAnchorIcon/anchorIcon/disableAnimation、
hover/press 状态切换、clicked 信号、键盘激活、主题。
"""

from __future__ import annotations

from unittest import mock

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest

from hero_side_ui import Link
from hero_side_ui.components.link.link import (
    DEFAULT_ANCHOR_ICON,
    _LinkIconLabel,
)
from hero_side_ui.components.text import Text
from hero_side_ui.themes import (
    LINK_OPACITY,
    LINK_SIZES,
    VALID_LINK_COLORS,
    VALID_LINK_SIZES,
    VALID_LINK_UNDERLINES,
)


# ------------------------------------------------------------
# 构造与默认值
# ------------------------------------------------------------
class TestLinkInit:
    def test_default(self, qtbot):
        w = Link()
        qtbot.addWidget(w)
        assert w._children_text == ""
        assert w._href == ""
        assert w._size == "md"
        assert w._color == "primary"
        assert w._underline == "none"
        assert w._is_block is False
        assert w._is_external is False
        assert w._is_disabled is False
        assert w._show_anchor_icon is False
        assert w._disable_animation is False
        assert w._theme_mode == "auto"
        assert isinstance(w._text, Text)
        assert w._icon is None

    def test_children_text_and_href(self, qtbot):
        w = Link("Click", href="https://heroui.com")
        qtbot.addWidget(w)
        assert w.children_text() == "Click"
        assert w.href() == "https://heroui.com"
        assert w._text.text() == "Click"

    def test_show_anchor_icon_mounts_default(self, qtbot):
        w = Link("Go", show_anchor_icon=True)
        qtbot.addWidget(w)
        assert isinstance(w._icon, _LinkIconLabel)
        assert w._icon._icon_name == DEFAULT_ANCHOR_ICON

    def test_custom_anchor_icon_str(self, qtbot):
        w = Link(
            "Help",
            show_anchor_icon=True,
            anchor_icon="material-symbols--help-outline",
        )
        qtbot.addWidget(w)
        assert isinstance(w._icon, _LinkIconLabel)
        assert w._icon._icon_name == "material-symbols--help-outline"

    def test_disabled_uses_arrow_cursor(self, qtbot):
        w = Link("X", is_disabled=True)
        qtbot.addWidget(w)
        assert w.cursor().shape() == Qt.CursorShape.ArrowCursor
        assert w.focusPolicy() == Qt.FocusPolicy.NoFocus

    def test_enabled_uses_pointing_hand(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        assert w.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert w.focusPolicy() == Qt.FocusPolicy.StrongFocus


# ------------------------------------------------------------
# 参数校验
# ------------------------------------------------------------
class TestLinkValidation:
    def test_invalid_size_raises(self):
        with pytest.raises(ValueError):
            Link(size="xl")

    def test_invalid_color_raises(self):
        with pytest.raises(ValueError):
            Link(color="cyan")

    def test_invalid_underline_raises(self):
        with pytest.raises(ValueError):
            Link(underline="dashed")


# ------------------------------------------------------------
# size
# ------------------------------------------------------------
class TestLinkSizes:
    @pytest.mark.parametrize("size", VALID_LINK_SIZES)
    def test_construct_all(self, qtbot, size):
        w = Link("X", size=size)
        qtbot.addWidget(w)
        assert w._size == size
        # 字号与 LINK_SIZES 表一致
        assert w._text.font().pixelSize() == LINK_SIZES[size]["font_size"]

    def test_set_size_updates_font(self, qtbot):
        w = Link("X", size="sm")
        qtbot.addWidget(w)
        w.set_size("lg")
        assert w._size == "lg"
        assert w._text.font().pixelSize() == LINK_SIZES["lg"]["font_size"]

    def test_set_size_idempotent(self, qtbot):
        w = Link(size="md")
        qtbot.addWidget(w)
        w.set_size("md")
        assert w._size == "md"


# ------------------------------------------------------------
# color
# ------------------------------------------------------------
class TestLinkColors:
    @pytest.mark.parametrize("color", VALID_LINK_COLORS)
    def test_construct_all(self, qtbot, color):
        w = Link("X", color=color)
        qtbot.addWidget(w)
        assert w._color == color

    def test_foreground_uses_theme_text_color_light(self, qtbot):
        w = Link("X", color="foreground", theme="light")
        qtbot.addWidget(w)
        assert w._text_color() == QColor("#18181b")

    def test_foreground_uses_theme_text_color_dark(self, qtbot):
        w = Link("X", color="foreground", theme="dark")
        qtbot.addWidget(w)
        assert w._text_color() == QColor("#ECEDEE")

    def test_set_color_pushes_to_text(self, qtbot):
        w = Link("X", color="primary")
        qtbot.addWidget(w)
        w.set_color("danger")
        assert w._color == "danger"
        # 文字色应被推送
        from hero_side_ui.themes import HEROUI_COLORS

        assert w._text.text_color == QColor(HEROUI_COLORS["danger"][500])


# ------------------------------------------------------------
# underline 五档
# ------------------------------------------------------------
class TestLinkUnderline:
    @pytest.mark.parametrize("u", VALID_LINK_UNDERLINES)
    def test_construct_all(self, qtbot, u):
        w = Link("X", underline=u)
        qtbot.addWidget(w)
        assert w._underline == u

    def test_none_no_underline_default(self, qtbot):
        w = Link("X", underline="none")
        qtbot.addWidget(w)
        assert w._text.font().underline() is False

    def test_always_underlined_immediately(self, qtbot):
        w = Link("X", underline="always")
        qtbot.addWidget(w)
        assert w._text.font().underline() is True

    def test_hover_underline_toggles(self, qtbot):
        w = Link("X", underline="hover")
        qtbot.addWidget(w)
        assert w._text.font().underline() is False
        w._is_hovered = True
        w._apply_text_underline()
        assert w._text.font().underline() is True
        w._is_hovered = False
        w._apply_text_underline()
        assert w._text.font().underline() is False

    def test_active_underline_toggles_with_press(self, qtbot):
        w = Link("X", underline="active")
        qtbot.addWidget(w)
        w._is_pressed = True
        w._apply_text_underline()
        assert w._text.font().underline() is True

    def test_focus_underline_toggles_with_focus(self, qtbot):
        w = Link("X", underline="focus")
        qtbot.addWidget(w)
        w._is_focused = True
        w._apply_text_underline()
        assert w._text.font().underline() is True

    def test_set_underline_dynamic(self, qtbot):
        w = Link("X", underline="none")
        qtbot.addWidget(w)
        w.set_underline("always")
        assert w._text.font().underline() is True


# ------------------------------------------------------------
# is_block
# ------------------------------------------------------------
class TestLinkIsBlock:
    def test_block_false_zero_padding(self, qtbot):
        w = Link("X", is_block=False)
        qtbot.addWidget(w)
        m = w._layout.contentsMargins()
        assert (m.left(), m.top(), m.right(), m.bottom()) == (0, 0, 0, 0)

    def test_block_true_uses_pad(self, qtbot):
        w = Link("X", is_block=True, size="md")
        qtbot.addWidget(w)
        m = w._layout.contentsMargins()
        spec = LINK_SIZES["md"]
        assert (m.left(), m.right()) == (spec["block_pad_x"], spec["block_pad_x"])
        assert (m.top(), m.bottom()) == (spec["block_pad_y"], spec["block_pad_y"])

    def test_block_target_opacity_always_1(self, qtbot):
        w = Link("X", is_block=True)
        qtbot.addWidget(w)
        # block 模式 hover 不改 opacity（背景走色块）
        w._is_hovered = True
        assert w._target_opacity() == 1.0
        w._is_pressed = True
        assert w._target_opacity() == 1.0

    def test_set_is_block_toggle_padding(self, qtbot):
        w = Link("X", is_block=False)
        qtbot.addWidget(w)
        w.set_is_block(True)
        m = w._layout.contentsMargins()
        spec = LINK_SIZES["md"]
        assert m.left() == spec["block_pad_x"]
        w.set_is_block(False)
        m = w._layout.contentsMargins()
        assert m.left() == 0


# ------------------------------------------------------------
# opacity 状态机（is_block=False）
# ------------------------------------------------------------
class TestLinkOpacityStateMachine:
    def test_idle_opacity_1(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        assert w._target_opacity() == 1.0

    def test_hover_opacity_light(self, qtbot):
        w = Link("X", theme="light")
        qtbot.addWidget(w)
        w._is_hovered = True
        assert w._target_opacity() == LINK_OPACITY["hover_light"]

    def test_hover_opacity_dark(self, qtbot):
        w = Link("X", theme="dark")
        qtbot.addWidget(w)
        w._is_hovered = True
        assert w._target_opacity() == LINK_OPACITY["hover_dark"]

    def test_press_opacity_disabled_value(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w._is_pressed = True
        assert w._target_opacity() == LINK_OPACITY["disabled"]

    def test_disabled_opacity(self, qtbot):
        w = Link("X", is_disabled=True)
        qtbot.addWidget(w)
        assert w._target_opacity() == LINK_OPACITY["disabled"]


# ------------------------------------------------------------
# clicked / pressed / released 信号 + 鼠标交互
# ------------------------------------------------------------
class TestLinkClick:
    def test_mouse_click_emits_clicked(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        with qtbot.waitSignal(w.clicked, timeout=500):
            QTest.mouseClick(w, Qt.MouseButton.LeftButton)

    def test_mouse_press_emits_pressed(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        with qtbot.waitSignal(w.pressed, timeout=500):
            QTest.mousePress(w, Qt.MouseButton.LeftButton)
        QTest.mouseRelease(w, Qt.MouseButton.LeftButton)

    def test_disabled_click_does_not_emit(self, qtbot):
        w = Link("X", is_disabled=True)
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        n = {"v": 0}
        w.clicked.connect(lambda: n.update(v=n["v"] + 1))
        QTest.mouseClick(w, Qt.MouseButton.LeftButton)
        assert n["v"] == 0

    def test_release_outside_does_not_emit_clicked(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w.resize(80, 20)
        w.show()
        qtbot.waitExposed(w)
        n = {"v": 0}
        w.clicked.connect(lambda: n.update(v=n["v"] + 1))
        QTest.mousePress(w, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        QTest.mouseRelease(w, Qt.MouseButton.LeftButton, pos=QPoint(5000, 5000))
        assert n["v"] == 0


# ------------------------------------------------------------
# 键盘激活（Enter/Space）
# ------------------------------------------------------------
class TestLinkKeyboard:
    def test_enter_triggers_clicked(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        w.setFocus()
        with qtbot.waitSignal(w.clicked, timeout=500):
            QTest.keyClick(w, Qt.Key.Key_Return)

    def test_space_triggers_clicked(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        w.setFocus()
        with qtbot.waitSignal(w.clicked, timeout=500):
            QTest.keyClick(w, Qt.Key.Key_Space)

    def test_disabled_keyboard_no_click(self, qtbot):
        w = Link("X", is_disabled=True)
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        n = {"v": 0}
        w.clicked.connect(lambda: n.update(v=n["v"] + 1))
        QTest.keyClick(w, Qt.Key.Key_Return)
        assert n["v"] == 0


# ------------------------------------------------------------
# is_external + webbrowser
# ------------------------------------------------------------
class TestLinkExternal:
    def test_external_opens_url(self, qtbot):
        w = Link("X", href="https://heroui.com", is_external=True)
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        with mock.patch("hero_side_ui.components.link.link.webbrowser.open") as m_open:
            QTest.mouseClick(w, Qt.MouseButton.LeftButton)
            m_open.assert_called_once_with("https://heroui.com")

    def test_not_external_no_open(self, qtbot):
        w = Link("X", href="https://heroui.com", is_external=False)
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        with mock.patch("hero_side_ui.components.link.link.webbrowser.open") as m_open:
            QTest.mouseClick(w, Qt.MouseButton.LeftButton)
            m_open.assert_not_called()

    def test_external_without_href_no_crash(self, qtbot):
        w = Link("X", is_external=True)
        qtbot.addWidget(w)
        w.resize(80, 24)
        w.show()
        qtbot.waitExposed(w)
        with mock.patch("hero_side_ui.components.link.link.webbrowser.open") as m_open:
            QTest.mouseClick(w, Qt.MouseButton.LeftButton)
            m_open.assert_not_called()


# ------------------------------------------------------------
# anchor icon 动态切换
# ------------------------------------------------------------
class TestLinkAnchorIcon:
    def test_set_show_anchor_icon_mounts(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        assert w._icon is None
        w.set_show_anchor_icon(True)
        assert isinstance(w._icon, _LinkIconLabel)

    def test_set_show_anchor_icon_unmounts(self, qtbot):
        w = Link("X", show_anchor_icon=True)
        qtbot.addWidget(w)
        assert w._icon is not None
        w.set_show_anchor_icon(False)
        assert w._icon is None

    def test_set_anchor_icon_replaces(self, qtbot):
        w = Link("X", show_anchor_icon=True)
        qtbot.addWidget(w)
        first = w._icon
        w.set_anchor_icon("material-symbols--help-outline")
        assert w._icon is not first
        assert isinstance(w._icon, _LinkIconLabel)
        assert w._icon._icon_name == "material-symbols--help-outline"

    def test_set_anchor_icon_when_hidden_no_mount(self, qtbot):
        w = Link("X", show_anchor_icon=False)
        qtbot.addWidget(w)
        w.set_anchor_icon("material-symbols--help-outline")
        # 仍未挂载（hidden 状态只记录输入）
        assert w._icon is None
        assert w._anchor_icon_input == "material-symbols--help-outline"


# ------------------------------------------------------------
# disabled / setter
# ------------------------------------------------------------
class TestLinkSetters:
    def test_set_is_disabled_resets_state(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w._is_hovered = True
        w._is_pressed = True
        w.set_is_disabled(True)
        assert w._is_hovered is False
        assert w._is_pressed is False
        assert w.cursor().shape() == Qt.CursorShape.ArrowCursor

    def test_set_children(self, qtbot):
        w = Link("Old")
        qtbot.addWidget(w)
        w.set_children("New")
        assert w.children_text() == "New"
        assert w._text.text() == "New"

    def test_set_href(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w.set_href("https://example.com")
        assert w.href() == "https://example.com"

    def test_set_disable_animation(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w.set_disable_animation(True)
        assert w._disable_animation is True

    def test_set_is_external(self, qtbot):
        w = Link("X")
        qtbot.addWidget(w)
        w.set_is_external(True)
        assert w._is_external is True


# ------------------------------------------------------------
# 主题
# ------------------------------------------------------------
class TestLinkTheme:
    def test_fixed_light(self, qtbot):
        w = Link("X", theme="light")
        qtbot.addWidget(w)
        assert w._theme == "light"

    def test_fixed_dark(self, qtbot):
        w = Link("X", theme="dark")
        qtbot.addWidget(w)
        assert w._theme == "dark"

    def test_set_theme_to_dark(self, qtbot):
        w = Link("X", theme="light", color="foreground")
        qtbot.addWidget(w)
        w.set_theme("dark")
        assert w._theme == "dark"
        assert w._text_color() == QColor("#ECEDEE")

    def test_auto_follows_provider_toggle(self, qtbot):
        from hero_side_ui import ThemeProvider

        ThemeProvider._reset_for_test()
        provider = ThemeProvider.instance()
        provider.set_mode("light")

        w = Link("X", theme="auto")
        qtbot.addWidget(w)
        assert w._theme == "light"

        provider.toggle()
        assert w._theme == "dark"

        ThemeProvider._reset_for_test()


# ------------------------------------------------------------
# 静态元信息
# ------------------------------------------------------------
class TestLinkMeta:
    def test_valid_sizes(self):
        assert Link.valid_sizes() == VALID_LINK_SIZES

    def test_valid_colors(self):
        assert Link.valid_colors() == VALID_LINK_COLORS

    def test_valid_underlines(self):
        assert Link.valid_underlines() == VALID_LINK_UNDERLINES
