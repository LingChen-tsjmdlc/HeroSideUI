"""Spinner 测试 —— 6 variant × 6 color × 3 size 全矩阵 + 动态 API + 主题。"""

from __future__ import annotations

import pytest

from hero_side_ui import Spinner, ThemeProvider


VARIANTS = ["default", "simple", "gradient", "spinner", "wave", "dots"]
COLORS = ["default", "primary", "secondary",
          "success", "warning", "danger"]
SIZES = ["sm", "md", "lg"]


@pytest.fixture(autouse=True)
def reset_provider():
    ThemeProvider._reset_for_test()
    yield
    ThemeProvider._reset_for_test()


# ============================================================
# 初始化 / 默认值
# ============================================================
class TestSpinnerInit:
    def test_default(self, qtbot):
        sp = Spinner()
        qtbot.addWidget(sp)
        assert sp.variant() == "default"
        assert sp.color() == "primary"
        assert sp.size() == "md"
        assert sp.label() == ""

    def test_default_starts_two_drivers(self, qtbot):
        sp = Spinner(variant="default")
        qtbot.addWidget(sp)
        assert sp._driver_a.is_running()
        assert sp._driver_b.is_running()

    def test_non_default_starts_one_driver(self, qtbot):
        sp = Spinner(variant="simple")
        qtbot.addWidget(sp)
        assert sp._driver_a.is_running()
        assert not sp._driver_b.is_running()

    def test_invalid_variant_falls_back(self, qtbot):
        sp = Spinner(variant="not-a-thing")
        qtbot.addWidget(sp)
        assert sp.variant() == "default"

    def test_invalid_color_falls_back(self, qtbot):
        sp = Spinner(color="not-a-color")
        qtbot.addWidget(sp)
        assert sp.color() == "primary"

    def test_invalid_size_falls_back(self, qtbot):
        sp = Spinner(size="huge")
        qtbot.addWidget(sp)
        assert sp.size() == "md"


# ============================================================
# 全矩阵
# ============================================================
class TestSpinnerMatrix:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_variant(self, qtbot, variant):
        sp = Spinner(variant=variant)
        qtbot.addWidget(sp)
        assert sp.variant() == variant
        # canvas 尺寸 > 0
        assert sp._canvas.width() > 0

    @pytest.mark.parametrize("color", COLORS)
    def test_color(self, qtbot, color):
        sp = Spinner(color=color)
        qtbot.addWidget(sp)
        assert sp.color() == color
        assert sp._indicator_color().isValid()

    @pytest.mark.parametrize("size", SIZES)
    def test_size(self, qtbot, size):
        sp = Spinner(size=size)
        qtbot.addWidget(sp)
        assert sp.size() == size
        assert sp._canvas_diameter() > 0

    @pytest.mark.parametrize("variant", VARIANTS)
    @pytest.mark.parametrize("size", SIZES)
    def test_variant_size_combo(self, qtbot, variant, size):
        sp = Spinner(variant=variant, size=size)
        qtbot.addWidget(sp)
        d = sp._canvas_diameter()
        # wave/dots 在 lg 下 = 48
        if variant in ("wave", "dots") and size == "lg":
            assert d == 48
        elif size == "lg":
            assert d == 40
        elif size == "md":
            assert d == 32
        else:
            assert d == 20


# ============================================================
# Label
# ============================================================
class TestSpinnerLabel:
    def test_no_label_hidden(self, qtbot):
        sp = Spinner()
        qtbot.addWidget(sp)
        sp.show()
        assert not sp._label.isVisible()

    def test_label_visible(self, qtbot):
        sp = Spinner(label="Loading...")
        qtbot.addWidget(sp)
        sp.show()
        assert sp._label.text() == "Loading..."
        assert sp._label.isVisible()


# ============================================================
# 动态 API
# ============================================================
class TestSpinnerDynamicAPI:
    def test_set_variant(self, qtbot):
        sp = Spinner(variant="default")
        qtbot.addWidget(sp)
        sp.set_variant("dots")
        assert sp.variant() == "dots"
        # 切换到非 default 后第二条驱动停
        assert not sp._driver_b.is_running()

    def test_set_variant_back_to_default_starts_b(self, qtbot):
        sp = Spinner(variant="simple")
        qtbot.addWidget(sp)
        assert not sp._driver_b.is_running()
        sp.set_variant("default")
        assert sp._driver_b.is_running()

    def test_set_variant_invalid_keeps_old(self, qtbot):
        sp = Spinner(variant="dots")
        qtbot.addWidget(sp)
        sp.set_variant("not-real")
        assert sp.variant() == "dots"

    def test_set_variant_same_noop(self, qtbot):
        sp = Spinner(variant="dots")
        qtbot.addWidget(sp)
        sp.set_variant("dots")  # 不应炸
        assert sp.variant() == "dots"

    def test_set_color(self, qtbot):
        sp = Spinner()
        qtbot.addWidget(sp)
        sp.set_color("danger")
        assert sp.color() == "danger"

    def test_set_color_invalid_falls_back(self, qtbot):
        sp = Spinner()
        qtbot.addWidget(sp)
        sp.set_color("not-real")
        assert sp.color() == "primary"

    def test_set_size(self, qtbot):
        sp = Spinner(size="sm")
        qtbot.addWidget(sp)
        sp.set_size("lg")
        assert sp.size() == "lg"

    def test_set_size_invalid_noop(self, qtbot):
        sp = Spinner(size="md")
        qtbot.addWidget(sp)
        sp.set_size("huge")
        assert sp.size() == "md"

    def test_set_label(self, qtbot):
        sp = Spinner()
        qtbot.addWidget(sp)
        sp.set_label("Hello")
        assert sp.label() == "Hello"
        assert sp._label.text() == "Hello"

    def test_label_color_follows_spinner_color(self, qtbot):
        """label 自动跟随 spinner 主色（铁律 1）。"""
        sp = Spinner(color="primary", label="x")
        qtbot.addWidget(sp)
        primary = sp._label_qcolor().name()
        sp.set_color("danger")
        danger = sp._label_qcolor().name()
        assert primary != danger


# ============================================================
# 主题
# ============================================================
class TestSpinnerTheme:
    def test_auto_registers(self, qtbot):
        sp = Spinner(theme="auto")
        qtbot.addWidget(sp)
        assert sp in ThemeProvider.instance()._widgets

    def test_hardcoded_theme_not_registered(self, qtbot):
        sp = Spinner(theme="dark")
        qtbot.addWidget(sp)
        assert sp not in ThemeProvider.instance()._widgets
        assert sp._theme == "dark"

    def test_set_theme_to_auto_registers(self, qtbot):
        sp = Spinner(theme="dark")
        qtbot.addWidget(sp)
        sp.set_theme("auto")
        assert sp in ThemeProvider.instance()._widgets

    def test_set_theme_to_hard_unregisters(self, qtbot):
        sp = Spinner(theme="auto")
        qtbot.addWidget(sp)
        sp.set_theme("light")
        assert sp not in ThemeProvider.instance()._widgets
        assert sp._theme == "light"

    def test_provider_broadcast_updates_theme(self, qtbot):
        sp = Spinner(theme="auto")
        qtbot.addWidget(sp)
        sp._apply_provider_theme("dark")
        assert sp._theme == "dark"

    def test_current_color_uses_theme(self, qtbot):
        sp_light = Spinner(color="default", theme="light")
        sp_dark = Spinner(color="default", theme="dark")
        qtbot.addWidget(sp_light)
        qtbot.addWidget(sp_dark)
        assert sp_light._indicator_color().name() != sp_dark._indicator_color().name()


# ============================================================
# Paint smoke test —— 触发 paintEvent，确保不炸
# ============================================================
class TestSpinnerPaint:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_paint_runs(self, qtbot, variant):
        sp = Spinner(variant=variant, label="x")
        qtbot.addWidget(sp)
        sp.show()
        sp._canvas.repaint()
        # 没炸即过
