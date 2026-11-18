"""主题取值存放层：默认值、字号槽位绑定、只读视图与还原。"""

from __future__ import annotations

import pytest

from hero_side_ui.core.text_style import DEFAULT_TEXT_COLORS, SIZE_MAP
from hero_side_ui.themes import HEROUI_COLORS, RADIUS, theme_values
from hero_side_ui.themes.shadow import DEFAULT_SHADOW


@pytest.fixture(autouse=True)
def clean_theme_values():
    """每个测试前后把主题取值还原为默认值。"""
    theme_values.reset()
    theme_values.clear_read_flag()
    yield
    theme_values.reset()
    theme_values.clear_read_flag()


class TestDefaults:
    def test_surface_defaults(self):
        assert theme_values.get_background("light") == "#FAFBFD"
        assert theme_values.get_background("dark") == "#0D0D0F"
        assert theme_values.get_content_background("light") == "#FEFEFF"
        assert theme_values.get_content_background("dark") == "#18181B"
        assert theme_values.get_popup_background("dark") == "#27272A"
        assert theme_values.get_foreground("light") == "#11181C"
        assert theme_values.get_foreground("dark") == "#ECEDEE"

    def test_unknown_theme_falls_back_to_light(self):
        assert theme_values.get_foreground("whatever") == theme_values.get_foreground("light")

    def test_color_foreground_defaults(self):
        assert theme_values.get_color_foreground("primary", "light") == "#FEFEFF"
        assert theme_values.get_color_foreground("warning", "dark") == "#11181C"
        assert theme_values.get_color_foreground("default", "dark") == "#D4D4D8"
        assert theme_values.get_color_foreground("default", "light") == "#FEFEFF"

    def test_unknown_color_uses_primary(self):
        assert theme_values.get_color_foreground(
            "nope", "light"
        ) == theme_values.get_color_foreground("primary", "light")

    def test_no_pure_black_or_white_in_defaults(self):
        pure = {"#000000", "#ffffff"}
        values = []
        for pair in theme_values.DEFAULT_SURFACES.values():
            values += list(pair.values())
        for pair in theme_values.DEFAULT_COLOR_FOREGROUND.values():
            values += list(pair.values())
        for side in DEFAULT_SHADOW.values():
            for layers in side.values():
                values += [layer.color for layer in layers]
        assert not [v for v in values if v.lower() in pure]

    def test_neutral_is_gone(self):
        assert "neutral" not in HEROUI_COLORS
        assert set(HEROUI_COLORS) == set(theme_values.COLOR_NAMES)

    def test_radius_defaults_and_aliases(self):
        assert (RADIUS["sm"], RADIUS["md"], RADIUS["lg"]) == ("4px", "8px", "14px")
        assert RADIUS["small"] == RADIUS["sm"]
        assert RADIUS["large"] == RADIUS["lg"]


class TestApplyAndReset:
    def test_apply_colors_in_place_and_reset(self):
        ramp = {s: "#123456" for s in theme_values.COLOR_STEPS}
        before = dict(HEROUI_COLORS["primary"])
        theme_values.apply({"colors": {"primary": ramp}})
        assert HEROUI_COLORS["primary"][500] == "#123456"
        theme_values.reset()
        assert HEROUI_COLORS["primary"] == before

    def test_apply_radius_syncs_aliases(self):
        theme_values.apply({"radius": {"sm": 1, "md": 2, "lg": 3}})
        assert (RADIUS["sm"], RADIUS["small"]) == ("1px", "1px")
        assert (RADIUS["lg"], RADIUS["large"]) == ("3px", "3px")
        theme_values.reset()
        assert RADIUS["lg"] == "14px"

    def test_apply_surface_and_reset(self):
        theme_values.apply({"surfaces": {"background": {"light": "#111111", "dark": "#222222"}}})
        assert theme_values.get_background("dark") == "#222222"
        theme_values.reset()
        assert theme_values.get_background("dark") == "#0D0D0F"

    def test_read_flag(self):
        theme_values.clear_read_flag()
        assert not theme_values.was_read()
        theme_values.get_foreground("light")
        assert theme_values.was_read()
        theme_values.clear_read_flag()
        theme_values.get_background("light", mark=False)
        assert not theme_values.was_read()


class TestFontSlots:
    def test_font_default_sizes(self):
        assert theme_values.get_font_sizes() == {"xs": 10, "sm": 13, "md": 16, "lg": 19, "xl": 22}

    def test_slots_are_bound(self):
        # 预设里 126 条字号 + 由 Input 派生出的拷贝
        assert len(theme_values._font_slots) >= 126

    @pytest.mark.parametrize(
        "original,snapped",
        [(10, 10), (11, 10), (12, 13), (13, 13), (14, 13), (15, 16), (16, 16), (18, 19), (19, 19)],
    )
    def test_snap_rule_is_nearest_tier(self, original, snapped):
        tiers = sorted(theme_values.DEFAULT_FONT_SIZE.values())
        assert min(tiers, key=lambda t: (abs(t - original), t)) == snapped

    def test_all_slots_sit_on_tier_defaults(self):
        defaults = set(theme_values.DEFAULT_FONT_SIZE.values())
        for node, key, _tier, has_px in theme_values._font_slots:
            raw = node[key]
            value = int(raw[:-2]) if has_px else raw
            assert value in defaults, (key, raw)

    def test_changing_font_size_rewrites_slots_in_place(self):
        from hero_side_ui.themes import BUTTON_SIZES

        theme_values.apply({"font_size": {"xs": 11, "sm": 14, "md": 17, "lg": 20, "xl": 24}})
        # Button 四档字号绑定在 xs / sm / md / lg 档上
        assert BUTTON_SIZES["sm"]["font_size"] == "11px"
        assert BUTTON_SIZES["md"]["font_size"] == "14px"
        assert BUTTON_SIZES["lg"]["font_size"] == "17px"
        assert BUTTON_SIZES["xl"]["font_size"] == "20px"
        theme_values.reset()
        assert BUTTON_SIZES["md"]["font_size"] == "13px"

    def test_bind_rejects_off_tier_size(self):
        with pytest.raises(ValueError):
            theme_values.bind_font_slots([{"font_size": 15}])

    def test_bind_ignores_weights_and_size_names(self):
        before = len(theme_values._font_slots)
        theme_values.bind_font_slots([{"font_weight": 500, "text_size": "xs", "label": "x"}])
        assert len(theme_values._font_slots) == before


class TestReadOnlyViews:
    def test_size_map_tracks_tiers(self):
        assert SIZE_MAP["xs"] == 10 and SIZE_MAP["xl"] == 22
        assert SIZE_MAP["2xl"] == 24 and SIZE_MAP["9xl"] == 128
        theme_values.apply({"font_size": {"xs": 11, "sm": 14, "md": 17, "lg": 20, "xl": 24}})
        assert SIZE_MAP["md"] == 17
        assert SIZE_MAP["2xl"] == 24  # 常量不变

    def test_size_map_is_a_mapping(self):
        assert "sm" in SIZE_MAP and "nope" not in SIZE_MAP
        assert len(SIZE_MAP) == 13
        assert list(SIZE_MAP)[:5] == ["xs", "sm", "md", "lg", "xl"]

    def test_default_text_colors_follow_foreground(self):
        assert DEFAULT_TEXT_COLORS["light"] == "#11181C"
        theme_values.apply({"surfaces": {"foreground": {"light": "#222222", "dark": "#EEEEEE"}}})
        assert DEFAULT_TEXT_COLORS["light"] == "#222222"
        assert DEFAULT_TEXT_COLORS.get("unknown", "x") == "x"
