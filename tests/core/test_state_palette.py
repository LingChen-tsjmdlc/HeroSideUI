"""StatePalette 单元测试

验证 ``hero_side_ui.core.state_palette.StatePalette`` 的 API 行为。

测试策略：**精确锁定值 + 代表性组合**，避免全参数化爆炸。
所有测试都是纯函数调用，不需要 qtbot（但 conftest autouse 会附加 qtbot 开销）。
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor

from hero_side_ui import StatePalette
from hero_side_ui.themes import HEROUI_COLORS


VARIANTS = ("solid", "shadow", "flat", "faded", "bordered", "light")
COLORS = ("default", "primary", "danger")  # 代表：中性 / 主语义 / 另一语义
THEMES = ("light", "dark")


# ============================================================
# Smoke：API 合法性（不崩、返回 QColor）
# ============================================================


class TestSmokeApi:
    """每个方法至少覆盖所有 variant，至少每个 state 跑一次，确保不崩。"""

    def test_bg_all_variants_hover(self):
        for variant in VARIANTS:
            for color in COLORS:
                for theme in THEMES:
                    c = StatePalette.bg(variant, color, theme, "hover")
                    assert isinstance(c, QColor)

    def test_border_all_variants_hover(self):
        for variant in VARIANTS:
            for color in COLORS:
                for theme in THEMES:
                    c = StatePalette.border(variant, color, theme, "hover")
                    assert isinstance(c, QColor)

    def test_text_all_variants_hover(self):
        for variant in VARIANTS:
            for color in COLORS:
                for theme in THEMES:
                    c = StatePalette.text(variant, color, theme, "hover")
                    assert isinstance(c, QColor)

    def test_all_states_bg_smoke(self):
        for state in ("resting", "hover", "focus", "selected", "disabled"):
            c = StatePalette.bg("flat", "primary", "light", state)
            assert isinstance(c, QColor)

    def test_all_states_text_smoke(self):
        for state in ("resting", "hover", "focus", "selected", "disabled"):
            c = StatePalette.text("flat", "primary", "light", state)
            assert isinstance(c, QColor)


# ============================================================
# resting / disabled：bg & border 透明，text 走 default
# ============================================================


class TestRestingState:
    def test_resting_bg_transparent_across_variants(self):
        for variant in VARIANTS:
            c = StatePalette.bg(variant, "primary", "light", "resting")
            assert c.alpha() == 0, f"{variant} resting bg should be transparent"

    def test_disabled_bg_transparent(self):
        for variant in VARIANTS:
            c = StatePalette.bg(variant, "primary", "light", "disabled")
            assert c.alpha() == 0

    def test_resting_border_transparent(self):
        for variant in VARIANTS:
            c = StatePalette.border(variant, "primary", "light", "resting")
            assert c.alpha() == 0

    def test_resting_text_is_default_light(self):
        default = StatePalette.text_default("light")
        for variant in VARIANTS:
            c = StatePalette.text(variant, "primary", "light", "resting")
            assert c.name() == default.name()

    def test_resting_text_is_default_dark(self):
        default = StatePalette.text_default("dark")
        for variant in VARIANTS:
            c = StatePalette.text(variant, "primary", "dark", "resting")
            assert c.name() == default.name()


# ============================================================
# focus / selected 等同 hover
# ============================================================


class TestStateEquivalence:
    def test_focus_bg_equals_hover(self):
        for variant in VARIANTS:
            for color in COLORS:
                hover = StatePalette.bg(variant, color, "light", "hover")
                focus = StatePalette.bg(variant, color, "light", "focus")
                assert hover.name(QColor.NameFormat.HexArgb) == focus.name(
                    QColor.NameFormat.HexArgb
                )

    def test_selected_text_equals_hover(self):
        for variant in VARIANTS:
            for color in COLORS:
                hover = StatePalette.text(variant, color, "dark", "hover")
                selected = StatePalette.text(variant, color, "dark", "selected")
                assert hover.name() == selected.name()


# ============================================================
# 精确锁定值：bg（迁移前 listbox 的 _hover_bg 行为）
# ============================================================


class TestSpecificBgValues:
    def test_solid_default_light(self):
        c = StatePalette.bg("solid", "default", "light", "hover")
        assert c.name() == HEROUI_COLORS["default"][100].lower()

    def test_solid_default_dark(self):
        c = StatePalette.bg("solid", "default", "dark", "hover")
        assert c.name() == HEROUI_COLORS["default"][800].lower()

    def test_solid_primary_both_themes(self):
        assert (
            StatePalette.bg("solid", "primary", "light", "hover").name()
            == HEROUI_COLORS["primary"][500].lower()
        )
        assert (
            StatePalette.bg("solid", "primary", "dark", "hover").name()
            == HEROUI_COLORS["primary"][500].lower()
        )

    def test_shadow_same_as_solid(self):
        """shadow 和 solid 的 bg 逻辑一致。"""
        for color in COLORS:
            s = StatePalette.bg("solid", color, "light", "hover")
            sh = StatePalette.bg("shadow", color, "light", "hover")
            assert s.name() == sh.name()

    def test_flat_primary_light_has_alpha_20(self):
        c = StatePalette.bg("flat", "primary", "light", "hover")
        # /20 → alpha ≈ 0.20 × 255 = 51
        assert 48 <= c.alpha() <= 54
        rgb = QColor(HEROUI_COLORS["primary"][500])
        assert (c.red(), c.green(), c.blue()) == (rgb.red(), rgb.green(), rgb.blue())

    def test_flat_default_light_has_alpha_40(self):
        c = StatePalette.bg("flat", "default", "light", "hover")
        # default/40 → alpha ≈ 102
        assert 99 <= c.alpha() <= 105
        rgb = QColor(HEROUI_COLORS["default"][200])
        assert (c.red(), c.green(), c.blue()) == (rgb.red(), rgb.green(), rgb.blue())

    def test_faded_hover_bg_is_default_100_light(self):
        c = StatePalette.bg("faded", "primary", "light", "hover")
        assert c.name() == HEROUI_COLORS["default"][100].lower()

    def test_faded_hover_bg_is_default_800_dark(self):
        c = StatePalette.bg("faded", "primary", "dark", "hover")
        assert c.name() == HEROUI_COLORS["default"][800].lower()

    def test_bordered_hover_bg_transparent(self):
        c = StatePalette.bg("bordered", "primary", "light", "hover")
        assert c.alpha() == 0

    def test_light_hover_bg_transparent(self):
        c = StatePalette.bg("light", "primary", "dark", "hover")
        assert c.alpha() == 0


# ============================================================
# 精确锁定值：border
# ============================================================


class TestSpecificBorderValues:
    def test_bordered_default_light(self):
        c = StatePalette.border("bordered", "default", "light", "hover")
        assert c.name() == HEROUI_COLORS["default"][300].lower()

    def test_bordered_default_dark(self):
        c = StatePalette.border("bordered", "default", "dark", "hover")
        assert c.name() == HEROUI_COLORS["default"][600].lower()

    def test_bordered_primary(self):
        c = StatePalette.border("bordered", "primary", "light", "hover")
        assert c.name() == HEROUI_COLORS["primary"][500].lower()

    def test_faded_border_light(self):
        c = StatePalette.border("faded", "primary", "light", "hover")
        assert c.name() == HEROUI_COLORS["default"][200].lower()

    def test_faded_border_dark(self):
        c = StatePalette.border("faded", "primary", "dark", "hover")
        assert c.name() == HEROUI_COLORS["default"][700].lower()

    def test_other_variants_border_transparent(self):
        for variant in ("solid", "shadow", "flat", "light"):
            c = StatePalette.border(variant, "primary", "light", "hover")
            assert c.alpha() == 0, f"{variant} border should be transparent on hover"


# ============================================================
# 精确锁定值：text
# ============================================================


class TestSpecificTextValues:
    def test_solid_default_foreground(self):
        assert StatePalette.text("solid", "default", "light", "hover").name() == "#000000"
        assert StatePalette.text("solid", "default", "dark", "hover").name() == "#ffffff"

    def test_solid_colored_is_white(self):
        for color in ("primary", "danger", "success"):
            assert StatePalette.text("solid", color, "light", "hover").name() == "#ffffff"
            assert StatePalette.text("solid", color, "dark", "hover").name() == "#ffffff"

    def test_flat_colored_light_is_500(self):
        c = StatePalette.text("flat", "primary", "light", "hover")
        assert c.name() == HEROUI_COLORS["primary"][500].lower()

    def test_flat_colored_dark_is_400(self):
        c = StatePalette.text("flat", "primary", "dark", "hover")
        assert c.name() == HEROUI_COLORS["primary"][400].lower()

    def test_light_variant_default_is_default_500(self):
        c = StatePalette.text("light", "default", "light", "hover")
        assert c.name() == HEROUI_COLORS["default"][500].lower()

    def test_bordered_default_falls_to_text_default(self):
        hover = StatePalette.text("bordered", "default", "light", "hover")
        default = StatePalette.text_default("light")
        assert hover.name() == default.name()


# ============================================================
# 中性辅助色
# ============================================================


class TestNeutralHelpers:
    def test_text_default(self):
        assert StatePalette.text_default("light").name() == HEROUI_COLORS["default"][800].lower()
        assert StatePalette.text_default("dark").name() == HEROUI_COLORS["default"][100].lower()

    def test_text_description_dark_uses_400_for_contrast(self):
        # dark 模式故意用 400 而非 500，保证在 #0B0D12 上可见
        assert (
            StatePalette.text_description("dark").name()
            == HEROUI_COLORS["default"][400].lower()
        )
        assert (
            StatePalette.text_description("light").name()
            == HEROUI_COLORS["default"][500].lower()
        )

    def test_shortcut_border(self):
        assert (
            StatePalette.shortcut_border("light").name()
            == HEROUI_COLORS["default"][300].lower()
        )
        assert (
            StatePalette.shortcut_border("dark").name()
            == HEROUI_COLORS["default"][700].lower()
        )

    def test_divider(self):
        assert StatePalette.divider("light").name() == HEROUI_COLORS["default"][200].lower()
        assert StatePalette.divider("dark").name() == HEROUI_COLORS["default"][700].lower()


# ============================================================
# 复合便捷方法
# ============================================================


class TestSelectedIndicator:
    def test_matches_hover_text(self):
        """selected_indicator 跟随 text(hover)，符合 HeroUI text-inherit 语义。"""
        for variant in VARIANTS:
            for color in COLORS:
                for theme in THEMES:
                    ind = StatePalette.selected_indicator(variant, color, theme)
                    txt = StatePalette.text(variant, color, theme, "hover")
                    assert ind.name() == txt.name()


# ============================================================
# 降级行为
# ============================================================


class TestUnknownColorFallback:
    """未知 color 名不抛 KeyError，静默 fallback 到 default 色板。"""

    def test_bg_unknown_color_does_not_raise(self):
        # _pal("nonexistent") → default 色板；但 variant=solid 的外层判断
        # `if color == "default"` 走"彩色"分支，返回 default[500]
        c = StatePalette.bg("solid", "nonexistent", "light", "hover")
        assert c.name() == HEROUI_COLORS["default"][500].lower()

    def test_text_unknown_color_does_not_raise(self):
        c = StatePalette.text("flat", "nonexistent", "light", "hover")
        assert c.name() == HEROUI_COLORS["default"][500].lower()
