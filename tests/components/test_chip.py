"""Chip 组件测试"""

from __future__ import annotations

import pytest

from hero_side_ui import Chip

COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
VARIANTS = ("solid", "bordered", "light", "flat", "faded", "shadow", "dot")
RADII = ("none", "sm", "md", "lg", "full")
SIZES = ("sm", "md", "lg")


class TestChipInit:
    """构造参数与默认值"""

    def test_default_no_args(self, qtbot):
        c = Chip()
        qtbot.addWidget(c)
        assert c._color == "default"
        assert c._variant == "solid"
        assert c._size == "md"
        assert c._radius == "full"
        assert c._theme_mode == "auto"

    def test_custom_params(self, qtbot):
        c = Chip(
            "标签",
            color="danger",
            variant="bordered",
            size="lg",
            radius="md",
            theme="dark",
        )
        qtbot.addWidget(c)
        assert c._color == "danger"
        assert c._variant == "bordered"
        assert c._size == "lg"
        assert c._radius == "md"
        assert c._theme == "dark"
        assert c._label.text() == "标签"

    def test_invalid_size_falls_back_md(self, qtbot):
        c = Chip("X", size="xxl")
        qtbot.addWidget(c)
        assert c._size == "md"

    def test_closable_shows_close_button(self, qtbot):
        c = Chip("X", is_closable=True)
        qtbot.addWidget(c)
        c.show()
        assert c._is_closable
        assert c._close_btn.isVisible()

    def test_on_close_implies_closable_button(self, qtbot):
        c = Chip("X", on_close=lambda: None)
        qtbot.addWidget(c)
        c.show()
        assert c._close_btn.isVisible()

    def test_dot_visible_only_in_dot_variant(self, qtbot):
        c = Chip("X", variant="dot")
        qtbot.addWidget(c)
        c.show()
        assert c._dot.isVisible()
        c2 = Chip("X", variant="solid")
        qtbot.addWidget(c2)
        c2.show()
        assert not c2._dot.isVisible()


class TestChipText:
    """文字唯一入口铁律：标签必须是 Text 实例"""

    def test_label_is_text_component(self, qtbot):
        from hero_side_ui import Text

        c = Chip("标签")
        qtbot.addWidget(c)
        assert isinstance(c._label, Text)


class TestChipOneChar:
    """单字符圆形模式"""

    def test_single_char_is_one_char(self, qtbot):
        c = Chip("A")
        qtbot.addWidget(c)
        assert c._is_one_char

    def test_multi_char_not_one_char(self, qtbot):
        c = Chip("AB")
        qtbot.addWidget(c)
        assert not c._is_one_char

    def test_one_char_square_size(self, qtbot):
        from hero_side_ui.themes import CHIP_SIZES

        c = Chip("A", size="md")
        qtbot.addWidget(c)
        c.show()
        side = CHIP_SIZES["md"]["one_char_size"]
        assert c.width() == side
        assert c.height() == side

    def test_one_char_disabled_by_closable(self, qtbot):
        c = Chip("A", is_closable=True)
        qtbot.addWidget(c)
        assert not c._is_one_char

    def test_one_char_disabled_by_dot(self, qtbot):
        c = Chip("A", variant="dot")
        qtbot.addWidget(c)
        assert not c._is_one_char


class TestChipColors:
    @pytest.mark.parametrize("color", COLORS)
    def test_all_colors_construct(self, qtbot, color):
        c = Chip(color, color=color)
        qtbot.addWidget(c)
        assert c._color == color


class TestChipVariants:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_all_variants_construct(self, qtbot, variant):
        c = Chip(variant, variant=variant)
        qtbot.addWidget(c)
        c.show()
        assert c._variant == variant


class TestChipRadius:
    @pytest.mark.parametrize("radius", RADII)
    def test_all_radii_construct(self, qtbot, radius):
        c = Chip(radius, radius=radius)
        qtbot.addWidget(c)
        assert c._radius == radius


class TestChipSizes:
    @pytest.mark.parametrize("size", SIZES)
    def test_all_sizes_construct(self, qtbot, size):
        c = Chip(size, size=size)
        qtbot.addWidget(c)
        assert c._size == size


class TestChipSetters:
    def test_set_text(self, qtbot):
        c = Chip("Old")
        qtbot.addWidget(c)
        c.set_text("New")
        assert c.text() == "New"
        assert c._label.text() == "New"

    def test_set_color(self, qtbot):
        c = Chip("X", color="default")
        qtbot.addWidget(c)
        c.set_color("success")
        assert c._color == "success"

    def test_set_variant(self, qtbot):
        c = Chip("X", variant="solid")
        qtbot.addWidget(c)
        c.set_variant("dot")
        assert c._variant == "dot"
        c.show()
        assert c._dot.isVisible()

    def test_set_size(self, qtbot):
        c = Chip("X", size="sm")
        qtbot.addWidget(c)
        c.set_size("lg")
        assert c._size == "lg"

    def test_set_radius(self, qtbot):
        c = Chip("X", radius="md")
        qtbot.addWidget(c)
        c.set_radius("none")
        assert c._radius == "none"

    def test_set_disabled(self, qtbot):
        c = Chip("X")
        qtbot.addWidget(c)
        c.set_disabled(True)
        assert c._is_disabled
        assert not c.isEnabled()

    def test_set_closable_toggle(self, qtbot):
        c = Chip("X")
        qtbot.addWidget(c)
        c.show()
        c.set_closable(True)
        assert c._close_btn.isVisible()
        c.set_closable(False)
        assert not c._close_btn.isVisible()


class TestChipClose:
    def test_close_hides(self, qtbot):
        c = Chip("X", is_closable=True)
        qtbot.addWidget(c)
        c.show()
        c._handle_close()
        assert not c.isVisible()

    def test_closed_signal(self, qtbot):
        c = Chip("X", is_closable=True)
        qtbot.addWidget(c)
        c.show()
        with qtbot.waitSignal(c.closed, timeout=500):
            c._handle_close()

    def test_on_close_callback(self, qtbot):
        called = []
        c = Chip("X", is_closable=True, on_close=lambda: called.append(1))
        qtbot.addWidget(c)
        c.show()
        c._close_btn.click()
        assert called == [1]
        assert not c.isVisible()


class TestChipThemeIntegration:
    def test_auto_follows_provider(self, qtbot):
        from hero_side_ui import ThemeProvider

        ThemeProvider._reset_for_test()
        p = ThemeProvider.instance()
        p.set_mode("light")
        c = Chip("X")
        qtbot.addWidget(c)
        assert c._theme == "light"
        p.toggle()
        assert c._theme == "dark"
        ThemeProvider._reset_for_test()

    def test_fixed_theme_not_affected(self, qtbot):
        from hero_side_ui import ThemeProvider

        ThemeProvider._reset_for_test()
        p = ThemeProvider.instance()
        p.set_mode("light")
        c = Chip("X", theme="dark")
        qtbot.addWidget(c)
        assert c._theme == "dark"
        p.toggle()
        assert c._theme == "dark"
        ThemeProvider._reset_for_test()


class TestChipCombo:
    """笛卡尔积降级：representative subset"""

    _REP_COLORS = ("default", "primary", "danger")
    _REP_VARIANTS = ("solid", "flat", "bordered", "dot")

    @pytest.mark.parametrize("color", _REP_COLORS)
    @pytest.mark.parametrize("variant", _REP_VARIANTS)
    def test_combo_smoke(self, qtbot, color, variant):
        c = Chip(f"{color}", color=color, variant=variant)
        qtbot.addWidget(c)
        c.show()
        assert c._color == color
        assert c._variant == variant
