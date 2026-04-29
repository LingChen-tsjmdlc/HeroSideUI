"""Divider 组件测试"""

import pytest
from PySide6.QtWidgets import QSizePolicy

from hero_side_ui import Divider


class TestDividerInit:
    """构造参数测试"""

    def test_default_params(self, qtbot):
        """默认参数应该正确"""
        d = Divider()
        qtbot.addWidget(d)

        assert d._orientation == "horizontal"
        assert d._theme == "light"
        assert d._custom_color is None

    def test_horizontal_size_policy(self, qtbot):
        """水平分割线: 宽度 Expanding, 高度 Fixed"""
        d = Divider(orientation="horizontal")
        qtbot.addWidget(d)

        sp = d.sizePolicy()
        assert sp.horizontalPolicy() == QSizePolicy.Policy.Expanding
        assert sp.verticalPolicy() == QSizePolicy.Policy.Fixed

    def test_vertical_size_policy(self, qtbot):
        """垂直分割线: 宽度 Fixed, 高度 Expanding"""
        d = Divider(orientation="vertical")
        qtbot.addWidget(d)

        sp = d.sizePolicy()
        assert sp.horizontalPolicy() == QSizePolicy.Policy.Fixed
        assert sp.verticalPolicy() == QSizePolicy.Policy.Expanding

    def test_horizontal_fixed_height(self, qtbot):
        """水平分割线固定高度为 1px"""
        d = Divider(orientation="horizontal")
        qtbot.addWidget(d)

        assert d.maximumHeight() == 1

    def test_vertical_fixed_width(self, qtbot):
        """垂直分割线固定宽度为 1px"""
        d = Divider(orientation="vertical")
        qtbot.addWidget(d)

        assert d.maximumWidth() == 1

    def test_custom_color(self, qtbot):
        """自定义颜色应该正确传递"""
        d = Divider(color="#ff0000")
        qtbot.addWidget(d)

        assert d._custom_color == "#ff0000"

    def test_dark_theme(self, qtbot):
        """暗色主题应该正确传递"""
        d = Divider(theme="dark")
        qtbot.addWidget(d)

        assert d._theme == "dark"


class TestDividerThemes:
    """主题测试"""

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_both_themes(self, qtbot, theme):
        """两种主题都不应报错"""
        d = Divider(theme=theme)
        qtbot.addWidget(d)
        assert d._theme == theme

    @pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
    def test_both_orientations(self, qtbot, orientation):
        """两种方向都不应报错"""
        d = Divider(orientation=orientation)
        qtbot.addWidget(d)
        assert d._orientation == orientation


class TestDividerDynamicAPI:
    """动态 API 测试"""

    def test_set_orientation(self, qtbot):
        d = Divider(orientation="horizontal")
        qtbot.addWidget(d)

        d.set_orientation("vertical")
        assert d._orientation == "vertical"
        assert d.maximumWidth() == 1

    def test_set_theme(self, qtbot):
        d = Divider(theme="light")
        qtbot.addWidget(d)

        d.set_theme("dark")
        assert d._theme == "dark"

    def test_set_color(self, qtbot):
        d = Divider()
        qtbot.addWidget(d)

        d.set_color("#00ff00")
        assert d._custom_color == "#00ff00"

    def test_set_color_none_resets(self, qtbot):
        d = Divider(color="#ff0000")
        qtbot.addWidget(d)

        d.set_color(None)
        assert d._custom_color is None


class TestDividerCombinations:
    """组合测试"""

    @pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_all_combinations(self, qtbot, orientation, theme):
        """所有方向 x 主题组合都不应报错"""
        d = Divider(orientation=orientation, theme=theme)
        qtbot.addWidget(d)
        assert d._orientation == orientation
        assert d._theme == theme


class TestDividerText:
    """带文字的分割线"""

    def test_default_no_text(self, qtbot):
        d = Divider()
        qtbot.addWidget(d)
        assert d.text() == ""
        assert d.text_size() == 12
        # 无文字：保持 1px 实线高度
        assert d.height() == 1

    def test_with_text(self, qtbot):
        d = Divider(text="OR")
        qtbot.addWidget(d)
        assert d.text() == "OR"
        # 带文字：高度 > 1px，由字号决定
        assert d.height() > 1

    def test_custom_text_size(self, qtbot):
        d_small = Divider(text="OR", text_size=10)
        d_large = Divider(text="OR", text_size=20)
        qtbot.addWidget(d_small); qtbot.addWidget(d_large)
        # 字号越大，Divider 越高
        assert d_large.height() > d_small.height()

    def test_set_text_toggle(self, qtbot):
        """运行时 set_text 可在"纯线" <-> "带文字"之间切换"""
        d = Divider()
        qtbot.addWidget(d)
        h0 = d.height()
        d.set_text("Hello")
        h1 = d.height()
        assert h1 > h0
        d.set_text(None)
        assert d.height() == h0

    def test_set_text_size(self, qtbot):
        d = Divider(text="OR", text_size=12)
        qtbot.addWidget(d)
        h0 = d.height()
        d.set_text_size(24)
        assert d.height() > h0
        assert d.text_size() == 24

    def test_vertical_ignores_text(self, qtbot):
        """垂直方向设置 text 不会切到自绘模式（仍是纯线）"""
        d = Divider(orientation="vertical", text="OR")
        qtbot.addWidget(d)
        # 垂直方向：固定宽度 1px，不会变成带文字的自绘布局
        assert d.width() == 1
