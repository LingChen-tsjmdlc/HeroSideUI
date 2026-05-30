"""Alert 组件测试"""

from __future__ import annotations

import pytest

from hero_side_ui import Alert

COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
VARIANTS = ("solid", "bordered", "flat", "faded")
RADII = ("none", "sm", "md", "lg", "full")


class TestAlertInit:
    """构造参数与默认值"""

    def test_default_no_args(self, qtbot):
        """无参构造可正常工作"""
        a = Alert()
        qtbot.addWidget(a)
        assert a._color == "default"
        assert a._variant == "flat"
        assert a._radius == "md"
        assert a._theme_mode == "auto"
        # is_visible=True 的语义：未被 hide()，show() 后自然可见
        a.show()
        assert a.isVisible()

    def test_custom_params(self, qtbot):
        a = Alert(
            title="标题",
            description="描述",
            color="danger",
            variant="bordered",
            radius="lg",
            theme="dark",
        )
        qtbot.addWidget(a)
        assert a._color == "danger"
        assert a._variant == "bordered"
        assert a._radius == "lg"
        assert a._theme == "dark"
        assert a._title_label.text() == "标题"
        assert a._desc_label.text() == "描述"

    def test_hidden_initially(self, qtbot):
        a = Alert(title="Hidden", is_visible=False)
        qtbot.addWidget(a)
        assert not a.isVisible()

    def test_closable_initially(self, qtbot):
        a = Alert(title="X", is_closable=True)
        qtbot.addWidget(a)
        a.show()
        assert a._is_closable
        assert a._close_btn.isVisible()

    def test_hide_icon(self, qtbot):
        a = Alert(title="X", hide_icon=True)
        qtbot.addWidget(a)
        a.show()
        assert a._hide_icon
        # hide_icon: icon + 圆形容器都不要
        assert not a._icon_wrapper.isVisible()
        assert a._layout.spacing() == 0

    def test_hide_icon_wrapper(self, qtbot):
        a = Alert(title="X", hide_icon_wrapper=True)
        qtbot.addWidget(a)
        a.show()
        assert a._hide_icon_wrapper
        # hide_icon_wrapper: 去掉圆形底色，保留 icon
        assert a._icon_wrapper.isVisible()
        assert a._icon_label.isVisible()


class TestAlertColors:
    """颜色遍历"""

    @pytest.mark.parametrize("color", COLORS)
    def test_all_colors_construct(self, qtbot, color):
        a = Alert(title=color, color=color)
        qtbot.addWidget(a)
        assert a._color == color


class TestAlertVariants:
    """变体遍历"""

    @pytest.mark.parametrize("variant", VARIANTS)
    def test_all_variants_construct(self, qtbot, variant):
        a = Alert(title=variant, variant=variant)
        qtbot.addWidget(a)
        assert a._variant == variant


class TestAlertRadius:
    """圆角遍历"""

    @pytest.mark.parametrize("radius", RADII)
    def test_all_radii_construct(self, qtbot, radius):
        a = Alert(title=radius, radius=radius)
        qtbot.addWidget(a)
        assert a._radius == radius


class TestAlertSetters:
    """动态 setter"""

    def test_set_color(self, qtbot):
        a = Alert(title="X", color="default")
        qtbot.addWidget(a)
        a.set_color("success")
        assert a._color == "success"

    def test_set_variant(self, qtbot):
        a = Alert(title="X", variant="flat")
        qtbot.addWidget(a)
        a.set_variant("solid")
        assert a._variant == "solid"

    def test_set_radius(self, qtbot):
        a = Alert(title="X", radius="md")
        qtbot.addWidget(a)
        a.set_radius("full")
        assert a._radius == "full"

    def test_set_title(self, qtbot):
        a = Alert(title="Old")
        qtbot.addWidget(a)
        a.set_title("New")
        assert a._title_label.text() == "New"

    def test_set_description(self, qtbot):
        a = Alert(title="X", description="Old")
        qtbot.addWidget(a)
        a.set_description("New")
        assert a._desc_label.text() == "New"

    def test_set_icon_custom(self, qtbot):
        a = Alert(title="X", color="primary")
        qtbot.addWidget(a)
        a.set_icon("heroicons--check-solid")
        assert a._icon_src == "heroicons--check-solid"

    def test_set_icon_restore(self, qtbot):
        a = Alert(title="X", color="primary")
        qtbot.addWidget(a)
        a.set_icon("heroicons--check-solid")
        a.set_icon(None)
        assert a._icon_src is None

    def test_set_visible_toggle(self, qtbot):
        a = Alert(title="X")
        qtbot.addWidget(a)
        a.set_visible(False)
        assert not a.isVisible()
        a.set_visible(True)
        assert a.isVisible()

    def test_set_closable_toggle(self, qtbot):
        a = Alert(title="X")
        qtbot.addWidget(a)
        a.show()
        a.set_closable(True)
        assert a._close_btn.isVisible()
        a.set_closable(False)
        assert not a._close_btn.isVisible()


class TestAlertClose:
    """关闭逻辑"""

    def test_close_hides(self, qtbot):
        a = Alert(title="X")
        qtbot.addWidget(a)
        a.show()
        a.close()
        assert not a.isVisible()

    def test_closed_signal(self, qtbot):
        a = Alert(title="X")
        qtbot.addWidget(a)
        a.show()
        with qtbot.waitSignal(a.closed, timeout=500):
            a.close()

    def test_on_close_callback(self, qtbot):
        called = []
        a = Alert(title="X", is_closable=True, on_close=lambda: called.append(1))
        qtbot.addWidget(a)
        a.show()
        a._close_btn.click()
        assert called == [1]
        assert not a.isVisible()


class TestAlertThemeIntegration:
    """ThemeProvider 联动"""

    def test_auto_follows_provider(self, qtbot):
        from hero_side_ui import ThemeProvider

        ThemeProvider._reset_for_test()
        p = ThemeProvider.instance()
        p.set_mode("light")
        a = Alert(title="X")
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
        a = Alert(title="X", theme="dark")
        qtbot.addWidget(a)
        assert a._theme == "dark"
        p.toggle()
        assert a._theme == "dark"
        ThemeProvider._reset_for_test()

    def test_custom_styled_survives_theme_switch(self, qtbot):
        """set_stylesheet 后主题切换不覆盖自定义 QSS"""
        a = Alert(title="X", color="primary", variant="flat")
        qtbot.addWidget(a)
        a.show()
        a.set_stylesheet("QWidget#HeroAlert { background: #ff00ff; }")
        assert a._custom_styled is True
        # 模拟主题切换
        a._apply_provider_theme("dark")
        # QSS 不应被覆盖
        assert "#ff00ff" in a.styleSheet()


class TestAlertCombo:
    """笛卡尔积降级：representative subset"""

    _REP_COLORS = ("default", "primary", "danger")
    _REP_VARIANTS = ("solid", "flat", "bordered")

    @pytest.mark.parametrize("color", _REP_COLORS)
    @pytest.mark.parametrize("variant", _REP_VARIANTS)
    def test_combo_smoke(self, qtbot, color, variant):
        a = Alert(title=f"{color} {variant}", color=color, variant=variant)
        qtbot.addWidget(a)
        a.show()
        assert a._color == color
        assert a._variant == variant
