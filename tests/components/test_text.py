"""Text / Title / Subtitle / Caption / Body 主题感知文字组件测试

新版 ``Text`` 是统一的主题感知文字组件，旧的 ``Title/Subtitle/Caption/Body``
都基于它实现，向后兼容。测试覆盖：
- 默认主题色按 light/dark 取自 _DEFAULT_TEXT_COLORS
- color 接受 HeroUI token / HEX / RGBA / tuple / QColor
- transparency 叠加在 color 自身 alpha 上
- size / weight 映射 (Tailwind token + int)
- 鼠标框选 palette.Highlight 跟随主题变化
- auto 模式注册到 ThemeProvider；hardcode 模式不注册
- Title 三档 level；Subtitle/Caption/Body 默认色阶
"""

from __future__ import annotations

import re

import pytest

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette

from hero_side_ui import (
    ThemeProvider, Text, Title, Subtitle, Caption, Body,
)


@pytest.fixture(autouse=True)
def reset_provider():
    """每个测试前后重置 ThemeProvider 单例和 Text 选区状态"""
    ThemeProvider._reset_for_test()
    Text._last_selection_owner = None
    yield
    ThemeProvider._reset_for_test()
    Text._last_selection_owner = None


# ============================================================
# 通用断言工具
# ============================================================
_RGBA_HEX_RE = re.compile(
    r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)",
    re.IGNORECASE,
)


def _stylesheet_color(widget) -> str:
    """从 widget.styleSheet() 抽出 color 值并归一化为小写 hex (alpha=1) 或 rgba 字符串。

    新版 Text 用 rgba(r, g, b, a) 写文字色（保留 alpha）。当 alpha=1 时把它
    转成 6 位 hex（兼容旧测试断言）；alpha<1 时保留 rgba 形式。
    """
    ss = widget.styleSheet().lower()
    if "color:" not in ss:
        return ""
    after = ss.split("color:", 1)[1]
    raw = after.split(";", 1)[0].strip()
    m = _RGBA_HEX_RE.search(raw)
    if not m:
        return raw
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    a = float(m.group(4))
    if a >= 0.999:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r}, {g}, {b}, {a:.4f})"


# ============================================================
# Text - 基础构造
# ============================================================
class TestTextBasics:
    def test_default_params(self, qtbot):
        t = Text("Hello")
        qtbot.addWidget(t)
        assert t.text() == "Hello"
        assert t._theme_mode == "auto"
        assert t._color_input is None

    def test_default_size_md(self, qtbot):
        t = Text("Hi")
        qtbot.addWidget(t)
        assert t.font().pixelSize() == 14
        assert t.font().weight() == QFont.Weight.Normal

    def test_default_color_light(self, qtbot):
        t = Text("Hi", theme="light")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#27272a"

    def test_default_color_dark(self, qtbot):
        t = Text("Hi", theme="dark")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#e4e4e7"


# ============================================================
# Text - size 映射
# ============================================================
class TestTextSize:
    @pytest.mark.parametrize("token,expected", [
        ("xs", 12), ("sm", 13), ("md", 14), ("lg", 16), ("xl", 18),
        ("2xl", 24), ("3xl", 30), ("4xl", 36), ("5xl", 48),
        ("6xl", 60), ("7xl", 72), ("8xl", 96), ("9xl", 128),
    ])
    def test_size_tokens(self, qtbot, token, expected):
        t = Text("Hi", size=token)
        qtbot.addWidget(t)
        assert t.font().pixelSize() == expected

    def test_size_int(self, qtbot):
        t = Text("Hi", size=22)
        qtbot.addWidget(t)
        assert t.font().pixelSize() == 22

    def test_size_unknown_falls_back_to_md(self, qtbot):
        t = Text("Hi", size="unknown_token")
        qtbot.addWidget(t)
        assert t.font().pixelSize() == 14

    def test_set_size_dynamic(self, qtbot):
        t = Text("Hi", size="md")
        qtbot.addWidget(t)
        t.set_size("3xl")
        assert t.font().pixelSize() == 30


# ============================================================
# Text - weight 映射
# ============================================================
class TestTextWeight:
    @pytest.mark.parametrize("token,expected", [
        ("thin", 100), ("extralight", 200), ("light", 300),
        ("normal", 400), ("regular", 400),
        ("medium", 500), ("semibold", 600), ("bold", 700),
        ("extrabold", 800), ("black", 900),
    ])
    def test_weight_tokens(self, qtbot, token, expected):
        t = Text("Hi", weight=token)
        qtbot.addWidget(t)
        assert int(t.font().weight()) == expected

    def test_weight_qfont_enum(self, qtbot):
        t = Text("Hi", weight=QFont.Weight.Bold)
        qtbot.addWidget(t)
        assert int(t.font().weight()) == 700

    def test_weight_int(self, qtbot):
        t = Text("Hi", weight=550)
        qtbot.addWidget(t)
        assert int(t.font().weight()) == 550


# ============================================================
# Text - color 解析
# ============================================================
class TestTextColor:
    def test_token_primary(self, qtbot):
        t = Text("Hi", color="primary", theme="light")
        qtbot.addWidget(t)
        # primary-500 = #006FEE
        assert _stylesheet_color(t) == "#006fee"

    def test_token_with_shade(self, qtbot):
        t = Text("Hi", color="primary-700", theme="light")
        qtbot.addWidget(t)
        # primary-700 = #004493
        assert _stylesheet_color(t) == "#004493"

    def test_token_default_700(self, qtbot):
        t = Text("Hi", color="default-700", theme="light")
        qtbot.addWidget(t)
        # default-700 = #3f3f46
        assert _stylesheet_color(t) == "#3f3f46"

    def test_hex(self, qtbot):
        t = Text("Hi", color="#FF8800", theme="light")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#ff8800"

    def test_hex_with_alpha(self, qtbot):
        # Qt 把 8 位 hex 当作 #AARRGGBB（不是 #RRGGBBAA）
        # 所以这里 AA=80 (alpha~0.5), RR=00, GG=66, BB=FF
        t = Text("Hi", color="#800066FF", theme="light")
        qtbot.addWidget(t)
        result = _stylesheet_color(t)
        assert result.startswith("rgba(0, 102, 255")

    def test_rgb_string(self, qtbot):
        t = Text("Hi", color="rgb(220, 38, 38)", theme="light")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#dc2626"

    def test_rgba_string_float_alpha(self, qtbot):
        t = Text("Hi", color="rgba(0, 200, 100, 0.7)", theme="light")
        qtbot.addWidget(t)
        result = _stylesheet_color(t)
        assert result.startswith("rgba(0, 200, 100")

    def test_tuple_rgb(self, qtbot):
        t = Text("Hi", color=(255, 0, 0), theme="light")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#ff0000"

    def test_tuple_rgba(self, qtbot):
        t = Text("Hi", color=(255, 0, 0, 128), theme="light")
        qtbot.addWidget(t)
        result = _stylesheet_color(t)
        assert result.startswith("rgba(255, 0, 0")

    def test_qcolor(self, qtbot):
        t = Text("Hi", color=QColor("#00ff00"), theme="dark")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#00ff00"

    def test_invalid_color_falls_back_to_default(self, qtbot):
        t = Text("Hi", color="not_a_color_at_all_123", theme="light")
        qtbot.addWidget(t)
        # 回退到主题默认正文色
        assert _stylesheet_color(t) == "#27272a"

    def test_set_color_none_restores_theme(self, qtbot):
        t = Text("Hi", color="#ff0000", theme="dark")
        qtbot.addWidget(t)
        t.set_color(None)
        assert _stylesheet_color(t) == "#e4e4e7"

    def test_set_color_dynamic(self, qtbot):
        t = Text("Hi", theme="light")
        qtbot.addWidget(t)
        t.set_color("primary")
        assert _stylesheet_color(t) == "#006fee"


# ============================================================
# Text - transparency
# ============================================================
class TestTextTransparency:
    def test_default_full(self, qtbot):
        t = Text("Hi", color="primary", theme="light")
        qtbot.addWidget(t)
        # alpha=1.0 → 6 位 hex
        assert _stylesheet_color(t) == "#006fee"

    def test_half(self, qtbot):
        t = Text("Hi", color="primary", transparency=0.5, theme="light")
        qtbot.addWidget(t)
        result = _stylesheet_color(t)
        assert "rgba(0, 111, 238" in result
        assert "0.50" in result  # alpha ~ 0.5

    def test_zero_full_transparent(self, qtbot):
        t = Text("Hi", color="primary", transparency=0.0, theme="light")
        qtbot.addWidget(t)
        result = _stylesheet_color(t)
        assert "0.0000" in result

    def test_clamp_above_one(self, qtbot):
        t = Text("Hi", color="primary", transparency=2.5, theme="light")
        qtbot.addWidget(t)
        # 1.0 上限
        assert _stylesheet_color(t) == "#006fee"

    def test_clamp_below_zero(self, qtbot):
        t = Text("Hi", color="primary", transparency=-1.0, theme="light")
        qtbot.addWidget(t)
        result = _stylesheet_color(t)
        assert "0.0000" in result

    def test_compound_with_color_alpha(self, qtbot):
        # color 自身 alpha=128 (~0.5) × transparency=0.5 → ~0.25
        t = Text("Hi", color=(255, 0, 0, 128), transparency=0.5, theme="light")
        qtbot.addWidget(t)
        result = _stylesheet_color(t)
        # 期望 ~ 0.25 alpha
        assert "rgba(255, 0, 0" in result
        # 简单 sanity：alpha 字段在 0.20~0.30 之间
        m = _RGBA_HEX_RE.search(t.styleSheet().lower())
        assert m is not None
        assert 0.20 <= float(m.group(4)) <= 0.30

    def test_set_transparency_dynamic(self, qtbot):
        t = Text("Hi", color="primary", theme="light")
        qtbot.addWidget(t)
        t.set_transparency(0.5)
        assert "0.50" in _stylesheet_color(t)


# ============================================================
# Text - 选区高亮 palette
# ============================================================
class TestTextSelectionPalette:
    def test_light_highlight_is_primary_alpha(self, qtbot):
        t = Text("Hi", theme="light")
        qtbot.addWidget(t)
        hl = t.palette().color(QPalette.ColorRole.Highlight)
        # 应该是 primary-500 (#006FEE) 半透明
        assert hl.red() == 0
        assert hl.green() == 0x6F
        assert hl.blue() == 0xEE
        # 亮色 0.22 alpha
        assert 0.20 <= hl.alphaF() <= 0.25

    def test_dark_highlight_is_primary_alpha(self, qtbot):
        t = Text("Hi", theme="dark")
        qtbot.addWidget(t)
        hl = t.palette().color(QPalette.ColorRole.Highlight)
        assert hl.red() == 0 and hl.green() == 0x6F and hl.blue() == 0xEE
        assert 0.30 <= hl.alphaF() <= 0.40

    def test_highlight_updates_on_theme_switch(self, qtbot):
        provider = ThemeProvider.instance()
        provider.set_mode("light")
        t = Text("Hi")
        qtbot.addWidget(t)
        light_hl = t.palette().color(QPalette.ColorRole.Highlight)
        provider.set_mode("dark")
        dark_hl = t.palette().color(QPalette.ColorRole.Highlight)
        # 暗色 alpha 应该比亮色高
        assert dark_hl.alphaF() > light_hl.alphaF()

    # ---- 新增：选中文字颜色（与原文字色无关）----
    def test_light_highlighted_text_is_dark(self, qtbot):
        """亮色模式：无论原文字色是什么，选中文字永远是暗色 #18181b"""
        t = Text("Hi", theme="light")
        qtbot.addWidget(t)
        fg = t.palette().color(QPalette.ColorRole.HighlightedText)
        assert fg.red() == 0x18 and fg.green() == 0x18 and fg.blue() == 0x1b

    def test_dark_highlighted_text_is_light(self, qtbot):
        """暗色模式：无论原文字色是什么，选中文字永远是亮色 #fafafa"""
        t = Text("Hi", theme="dark")
        qtbot.addWidget(t)
        fg = t.palette().color(QPalette.ColorRole.HighlightedText)
        assert fg.red() == 0xFA and fg.green() == 0xFA and fg.blue() == 0xFA

    def test_highlighted_text_ignores_custom_color(self, qtbot):
        """即使用户设了自定义文字色，选中文字色仍跟随主题"""
        t = Text("Hi", color="#FF8800", theme="light")
        qtbot.addWidget(t)
        fg = t.palette().color(QPalette.ColorRole.HighlightedText)
        # 仍然是 #18181b，不是 #FF8800
        assert fg.red() == 0x18 and fg.green() == 0x18 and fg.blue() == 0x1b


# ============================================================
# Text - auto 模式跟随 ThemeProvider
# ============================================================
class TestTextAutoMode:
    def test_auto_registers_to_provider(self, qtbot):
        t = Text("Hi")
        qtbot.addWidget(t)
        assert ThemeProvider.instance().is_registered(t)

    def test_hardcode_does_not_register(self, qtbot):
        t = Text("Hi", theme="light")
        qtbot.addWidget(t)
        assert not ThemeProvider.instance().is_registered(t)

    def test_provider_toggle_updates_color(self, qtbot):
        provider = ThemeProvider.instance()
        provider.set_mode("light")
        t = Text("Hi")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#27272a"
        provider.set_mode("dark")
        assert _stylesheet_color(t) == "#e4e4e7"

    def test_set_theme_auto_to_hardcode_unregisters(self, qtbot):
        t = Text("Hi")
        qtbot.addWidget(t)
        assert ThemeProvider.instance().is_registered(t)
        t.set_theme("dark")
        assert not ThemeProvider.instance().is_registered(t)

    def test_set_theme_hardcode_to_auto_registers(self, qtbot):
        t = Text("Hi", theme="light")
        qtbot.addWidget(t)
        assert not ThemeProvider.instance().is_registered(t)
        t.set_theme("auto")
        assert ThemeProvider.instance().is_registered(t)


# ============================================================
# Title - level 三档
# ============================================================
class TestTitle:
    def test_default_params(self, qtbot):
        t = Title("Hello")
        qtbot.addWidget(t)
        assert t.text() == "Hello"
        assert t._theme_mode == "auto"

    def test_default_24_bold(self, qtbot):
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
        t = Title("Hi", level=99)
        qtbot.addWidget(t)
        assert t.font().pixelSize() == 24

    def test_light_uses_default_text_color(self, qtbot):
        # Title 没传 color → 用 Text 默认主题前景色
        t = Title("Hi", theme="light")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#27272a"

    def test_dark_uses_default_text_color(self, qtbot):
        t = Title("Hi", theme="dark")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#e4e4e7"


# ============================================================
# Subtitle / Caption / Body 默认值
# ============================================================
class TestLegacyAliases:
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
# 自定义 color 覆盖 (兼容旧测试)
# ============================================================
class TestColorOverride:
    def test_override_string(self, qtbot):
        t = Title("Hi", color="#ff0000", theme="light")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#ff0000"

    def test_override_qcolor(self, qtbot):
        t = Title("Hi", color=QColor("#00ff00"), theme="dark")
        qtbot.addWidget(t)
        assert _stylesheet_color(t) == "#00ff00"

    def test_override_persists_through_theme_change(self, qtbot):
        """覆盖色不随 set_theme 改变（仅文字色；选区底色仍跟主题）"""
        t = Title("Hi", color="#abcdef", theme="light")
        qtbot.addWidget(t)
        t.set_theme("dark")
        assert _stylesheet_color(t) == "#abcdef"

    def test_set_color_none_restores_theme(self, qtbot):
        """set_color(None) 恢复主题感知"""
        t = Title("Hi", color="#ff0000", theme="dark")
        qtbot.addWidget(t)
        t.set_color(None)
        # Title 现在的默认色 = Text 默认色 = #e4e4e7
        assert _stylesheet_color(t) == "#e4e4e7"

    def test_set_color_overrides(self, qtbot):
        t = Title("Hi", theme="light")
        qtbot.addWidget(t)
        t.set_color("#123456")
        assert _stylesheet_color(t) == "#123456"


# ============================================================
# 组合：所有别名 × 两主题构造不崩
# ============================================================
class TestCombinations:
    @pytest.mark.parametrize("cls", [Text, Title, Subtitle, Caption, Body])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_construct_all(self, qtbot, cls, theme):
        w = cls("Sample", theme=theme)
        qtbot.addWidget(w)
        assert w.text() == "Sample"
        assert _stylesheet_color(w) != ""


# ============================================================
# 选区管理（单选区互斥）
# ============================================================
class TestTextSelection:
    def test_click_focus_policy(self, qtbot):
        """Text 使用 ClickFocus，支持键盘选区扩展但不占 Tab 链"""
        t = Text("Hello")
        qtbot.addWidget(t)
        assert t.focusPolicy() == Qt.FocusPolicy.ClickFocus

    def test_clear_selection_keeps_text(self, qtbot):
        """_clear_selection 重置内部状态但不丢失文本内容"""
        t = Text("Hello World")
        qtbot.addWidget(t)
        t._clear_selection()
        assert t.text() == "Hello World"

    def test_clear_selection_idempotent_on_empty(self, qtbot):
        """_clear_selection 在空文本上不会崩溃"""
        t = Text("")
        qtbot.addWidget(t)
        t._clear_selection()
        assert t.text() == ""

    def test_last_selection_owner_class_var_exists(self, qtbot):
        """类变量 _last_selection_owner 存在且初始为 None"""
        assert hasattr(Text, '_last_selection_owner')
        assert Text._last_selection_owner is None
