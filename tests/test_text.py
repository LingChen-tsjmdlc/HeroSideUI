"""Title / Subtitle / Caption / Body 语义化文字组件测试

这 4 个组件是「开箱即用」铁律 5 的关键落地：让用户/demo 不用再写
`setStyleSheet("color: #...")`，主题切换自动跟。所以测试关注：
- 默认主题色按 light/dark 取自 _palette_map
- 用户传 color 覆盖后不再随主题切换
- auto 模式注册到 ThemeProvider；hardcode 模式不注册
- 字号/字重默认值（Title 三档 level）
"""

from __future__ import annotations

import pytest

from PySide6.QtGui import QColor, QFont

from hero_side_ui import ThemeProvider, Title, Subtitle, Caption, Body


@pytest.fixture(autouse=True)
def reset_provider():
    """每个测试前后重置 ThemeProvider 单例"""
    ThemeProvider._reset_for_test()
    yield
    ThemeProvider._reset_for_test()


# ============================================================
# 通用断言工具
# ============================================================
def _stylesheet_color(widget) -> str:
    """从 widget.styleSheet() 抽出 color 值（小写 hex）"""
    ss = widget.styleSheet().lower()
    # 形如 "qlabel { color: #18181b; background: transparent; }"
    if "color:" not in ss:
        return ""
    after = ss.split("color:", 1)[1]
    return after.split(";", 1)[0].strip()


# ============================================================
# Title
# ============================================================
class TestTitleInit:
    def test_default_params(self, qtbot):
        t = Title("Hello")
        qtbot.addWidget(t)
        assert t.text() == "Hello"
        assert t._theme_mode == "auto"
        assert t._color_override is None

    def test_default_font_24_bold(self, qtbot):
        """level=1（默认）→ 24px Bold"""
        t = Title("Hi")
        qtbot.addWidget(t)
        assert t.font().pixelSize() == 24
        assert t.font().weight() == QFont.Weight.Bold

    @pytest.mark.parametrize("level,expected_size", [(1, 24), (2, 18), (3, 16)])
    def test_level_sizes(self, qtbot, level, expected_size):
        t = Title("Hi", level=level)
        qtbot.addWidget(t)
        assert t.font().pixelSize() == expected_size

    def test_invalid_level_falls_back_to_24(self, qtbot):
        """不在 {1,2,3} 的 level 走默认 24"""
        t = Title("Hi", level=99)
        qtbot.addWidget(t)
        assert t.font().pixelSize() == 24

    def test_light_color(self, qtbot):
        t = Title("Hi", theme="light")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#18181b"

    def test_dark_color(self, qtbot):
        t = Title("Hi", theme="dark")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#fafafa"


# ============================================================
# Subtitle / Caption / Body 默认字号
# ============================================================
class TestOtherTextDefaults:
    def test_subtitle_default(self, qtbot):
        s = Subtitle("Sub", theme="light")
        qtbot.addWidget(s)
        assert s.font().pixelSize() == 13
        assert s.font().weight() == QFont.Weight.Normal
        assert _stylesheet_color(s) == "#71717a"

    def test_subtitle_dark(self, qtbot):
        s = Subtitle("Sub", theme="dark")
        qtbot.addWidget(s)
        assert _stylesheet_color(s) == "#a1a1aa"

    def test_caption_default(self, qtbot):
        c = Caption("Cap", theme="light")
        qtbot.addWidget(c)
        assert c.font().pixelSize() == 12
        assert _stylesheet_color(c) == "#a1a1aa"

    def test_caption_dark(self, qtbot):
        c = Caption("Cap", theme="dark")
        qtbot.addWidget(c)
        assert _stylesheet_color(c) == "#71717a"

    def test_body_default(self, qtbot):
        b = Body("Body", theme="light")
        qtbot.addWidget(b)
        assert b.font().pixelSize() == 14
        assert _stylesheet_color(b) == "#27272a"

    def test_body_dark(self, qtbot):
        b = Body("Body", theme="dark")
        qtbot.addWidget(b)
        assert _stylesheet_color(b) == "#e4e4e7"


# ============================================================
# 自定义 color 覆盖
# ============================================================
class TestColorOverride:
    def test_override_string(self, qtbot):
        """传 color="#ff0000" 后无视主题"""
        t = Title("Hi", color="#ff0000", theme="light")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#ff0000"

    def test_override_qcolor(self, qtbot):
        t = Title("Hi", color=QColor("#00ff00"), theme="dark")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#00ff00"

    def test_override_persists_through_theme_change(self, qtbot):
        """覆盖色不随 set_theme 改变"""
        t = Title("Hi", color="#abcdef", theme="light")
        qtbot.addWidget(t)
        t.set_theme("dark")
        assert _stylesheet_color(t) == "#abcdef"

    def test_set_color_none_restores_theme(self, qtbot):
        """set_color(None) 恢复主题感知"""
        t = Title("Hi", color="#ff0000", theme="dark")
        qtbot.addWidget(t)
        t.set_color(None)
        assert _stylesheet_color(t) == "#fafafa"

    def test_set_color_overrides(self, qtbot):
        t = Title("Hi", theme="light")
        qtbot.addWidget(t)
        t.set_color("#123456")
        assert _stylesheet_color(t) == "#123456"


# ============================================================
# auto 模式跟随 ThemeProvider
# ============================================================
class TestAutoMode:
    def test_auto_registers_to_provider(self, qtbot):
        t = Title("Hi")
        qtbot.addWidget(t)
        assert ThemeProvider.instance().is_registered(t)

    def test_hardcode_does_not_register(self, qtbot):
        t = Title("Hi", theme="light")
        qtbot.addWidget(t)
        assert not ThemeProvider.instance().is_registered(t)

    def test_provider_toggle_updates_color(self, qtbot):
        """auto 模式下 ThemeProvider 切主题，文字色跟随"""
        provider = ThemeProvider.instance()
        provider.set_mode("light")
        t = Title("Hi")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#18181b"

        provider.set_mode("dark")
        assert _stylesheet_color(t) == "#fafafa"

    def test_set_theme_auto_to_hardcode_unregisters(self, qtbot):
        """auto → hardcode 切换会从 provider 注销"""
        t = Subtitle("Hi")
        qtbot.addWidget(t)
        assert ThemeProvider.instance().is_registered(t)

        t.set_theme("dark")
        assert not ThemeProvider.instance().is_registered(t)
        assert _stylesheet_color(t) == "#a1a1aa"

    def test_set_theme_hardcode_to_auto_registers(self, qtbot):
        """hardcode → auto 切换会重新注册"""
        t = Body("Hi", theme="light")
        qtbot.addWidget(t)
        assert not ThemeProvider.instance().is_registered(t)

        t.set_theme("auto")
        assert ThemeProvider.instance().is_registered(t)
        assert t._theme_mode == "auto"


# ============================================================
# 组合：4 个组件 × 2 主题
# ============================================================
class TestCombinations:
    @pytest.mark.parametrize("cls", [Title, Subtitle, Caption, Body])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_construct_all(self, qtbot, cls, theme):
        """所有组件 × 两主题构造不崩"""
        w = cls("Sample", theme=theme)
        qtbot.addWidget(w)
        assert w.text() == "Sample"
        # 颜色非空
        assert _stylesheet_color(w) != ""
