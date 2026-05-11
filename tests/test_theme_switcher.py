"""ThemeSwitcher 单元测试"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor

from hero_side_ui import ThemeProvider, ThemeSwitcher


@pytest.fixture(autouse=True)
def reset_provider():
    """每个测试前后重置 ThemeProvider 单例"""
    ThemeProvider._reset_for_test()
    yield
    ThemeProvider._reset_for_test()


class TestThemeSwitcherInit:
    """初始化"""

    def test_default_params(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)

        # 默认始终注册到 provider（auto 模式）
        assert sw._theme_mode == "auto"
        assert ThemeProvider.instance().is_registered(sw)

        # 默认 icon_only=True + variant=flat
        assert sw._icon_only is True
        assert sw._variant == "flat"

        # 正方形：md size → 46×46（height 26 + padding_y 10×2）
        assert sw.size().width() == sw.size().height()
        assert sw.size().width() == 46
        assert sw.iconSize().width() == 24

    def test_size_sm(self, qtbot):
        sw = ThemeSwitcher(size="sm")
        qtbot.addWidget(sw)
        # sm: 18 + 6*2 = 30
        assert sw.size().width() == 30
        assert sw.size().width() == sw.size().height()
        assert sw.iconSize().width() == 16

    def test_size_lg(self, qtbot):
        sw = ThemeSwitcher(size="lg")
        qtbot.addWidget(sw)
        # lg: 33 + 14*2 = 61
        assert sw.size().width() == 61
        assert sw.size().width() == sw.size().height()
        assert sw.iconSize().width() == 32

    def test_custom_icon_size(self, qtbot):
        sw = ThemeSwitcher(icon_size=24)
        qtbot.addWidget(sw)
        assert sw.iconSize().width() == 24

    def test_default_colors(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        # 默认: 太阳 = 金黄
        assert sw._sun_color.name().lower() == "#f5a524"
        # 默认: 月亮 = 蓝色
        assert sw._moon_color.name().lower() == "#7dd3fc"

    def test_custom_colors_str(self, qtbot):
        sw = ThemeSwitcher(sun_color="#FF0000", moon_color="#00FF00")
        qtbot.addWidget(sw)
        assert sw._sun_color.name().lower() == "#ff0000"
        assert sw._moon_color.name().lower() == "#00ff00"

    def test_custom_colors_qcolor(self, qtbot):
        sw = ThemeSwitcher(sun_color=QColor(100, 50, 200))
        qtbot.addWidget(sw)
        assert sw._sun_color.red() == 100
        assert sw._sun_color.green() == 50
        assert sw._sun_color.blue() == 200

    def test_custom_icons(self, qtbot):
        sw = ThemeSwitcher(
            sun_icon="heroicons--check-solid",
            moon_icon="heroicons--x-circle-solid",
        )
        qtbot.addWidget(sw)
        assert sw._sun_icon_src == "heroicons--check-solid"
        assert sw._moon_icon_src == "heroicons--x-circle-solid"


class TestThemeSwitcherClick:
    """点击行为"""

    def test_click_toggles_provider(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        provider = ThemeProvider.instance()

        provider.set_mode("light")
        assert provider.current_theme == "light"

        sw.click()
        assert provider.current_theme == "dark"

        sw.click()
        assert provider.current_theme == "light"

    def test_icon_changes_with_theme(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        provider = ThemeProvider.instance()

        provider.set_mode("light")
        # icon 应该是太阳
        icon_light = sw.icon()
        assert not icon_light.isNull()

        provider.set_mode("dark")
        # icon 应该是月亮（不同 pixmap）
        icon_dark = sw.icon()
        assert not icon_dark.isNull()

        # 至少 cacheKey 应该不同（icon 已被替换）
        # 用 pixmap 大小来粗略验证
        pix_light = icon_light.pixmap(16, 16)
        pix_dark = icon_dark.pixmap(16, 16)
        assert pix_light.cacheKey() != pix_dark.cacheKey()


class TestThemeSwitcherDynamicAPI:
    """动态 setter"""

    def test_set_sun_color(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        sw.set_sun_color("#FFAA00")
        assert sw._sun_color.name().lower() == "#ffaa00"

    def test_set_moon_color(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        sw.set_moon_color("#0088FF")
        assert sw._moon_color.name().lower() == "#0088ff"

    def test_set_sun_icon(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        sw.set_sun_icon("heroicons--check-solid")
        assert sw._sun_icon_src == "heroicons--check-solid"

    def test_set_moon_icon(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        sw.set_moon_icon("heroicons--eye-solid")
        assert sw._moon_icon_src == "heroicons--eye-solid"

    def test_set_icon_size(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        sw.set_icon_size(20)
        assert sw._icon_size == 20
        assert sw.iconSize().width() == 20


class TestThemeSwitcherFollowsProvider:
    """跟随 provider 切换"""

    def test_provider_toggle_updates_switcher_theme(self, qtbot):
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)
        provider = ThemeProvider.instance()
        provider.set_mode("light")
        assert sw._theme == "light"

        provider.toggle()
        assert sw._theme == "dark"

    def test_set_theme_always_auto(self, qtbot):
        """ThemeSwitcher 不允许硬锁，始终是 auto"""
        sw = ThemeSwitcher()
        qtbot.addWidget(sw)

        # 试图硬锁 → 仍然是 auto
        sw.set_theme("dark")
        assert sw._theme_mode == "auto"
        assert ThemeProvider.instance().is_registered(sw)
