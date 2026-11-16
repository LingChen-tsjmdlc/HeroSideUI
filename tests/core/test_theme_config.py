"""setup() 新增主题参数的校验与应用（core/_theme_config.py + HeroSideUIProvider.setup）。"""

from __future__ import annotations

import warnings

import pytest
from PySide6.QtWidgets import QApplication

from hero_side_ui import HeroSideUIProvider, ThemeProvider
from hero_side_ui.core import _theme_config, shadow_paint
from hero_side_ui.themes import HEROUI_COLORS, RADIUS, theme_values

ROSE = [
    "#fff1f2", "#ffe4e6", "#fecdd3", "#fda4af", "#fb7185",
    "#e11d48", "#be123c", "#9f1239", "#881337", "#4c0519",
]  # fmt: skip


@pytest.fixture(autouse=True)
def clean_theme_values(qapp):
    ThemeProvider._reset_for_test()
    theme_values.reset()
    theme_values.clear_read_flag()
    yield
    HeroSideUIProvider.teardown()
    ThemeProvider._reset_for_test()
    theme_values.reset()
    theme_values.clear_read_flag()
    shadow_paint.clear_cache()


def _errors(**kwargs) -> str:
    with pytest.raises(ValueError) as exc:
        _theme_config.validate(**kwargs)
    return str(exc.value)


class TestColors:
    def test_valid_ramp_as_list_and_dict(self):
        cfg = _theme_config.validate(
            colors={"primary": ROSE, "danger": dict(zip(theme_values.COLOR_STEPS, ROSE))},
            color_foreground={"primary": "#FEFEFF", "danger": "#FEFEFF"},
        )
        assert cfg["colors"]["primary"][500] == "#e11d48"
        assert cfg["colors"]["danger"][900] == "#4c0519"

    def test_wrong_length_unknown_name_and_bad_hex_are_reported_together(self):
        msg = _errors(colors={"primary": ["#fff"] * 3, "pink": ROSE, "danger": ["red"] * 10})
        assert "必须写满 10 阶" in msg
        assert "未知色名 'pink'" in msg
        assert "#RRGGBB" in msg

    def test_changed_ramp_requires_color_foreground(self):
        assert "请同时在 color_foreground 里写 'primary'" in _errors(colors={"primary": ROSE})

    def test_non_monotone_ramp_only_warns(self):
        cfg = _theme_config.validate(
            colors={"primary": list(reversed(ROSE))}, color_foreground={"primary": "#FEFEFF"}
        )
        assert any("从浅到深" in w for w in cfg["warnings"])

    def test_unchanged_defaults_do_not_warn(self):
        cfg = _theme_config.validate(
            colors={"success": [HEROUI_COLORS["success"][s] for s in theme_values.COLOR_STEPS]},
            color_foreground={"success": "#FEFEFF"},
        )
        assert cfg["warnings"] == []


class TestColorForeground:
    def test_single_hex_applies_to_both_themes(self):
        cfg = _theme_config.validate(color_foreground={"primary": "#112233"})
        assert cfg["color_foreground"]["primary"] == {"light": "#112233", "dark": "#112233"}

    def test_pair_and_bad_values(self):
        cfg = _theme_config.validate(
            color_foreground={"default": {"light": "#FFFFFF", "dark": "#D4D4D8"}}
        )
        assert cfg["color_foreground"]["default"]["dark"] == "#D4D4D8"
        msg = _errors(color_foreground={"nope": "#FFFFFF", "primary": {"light": "#FFF"}})
        assert "未知色名" in msg and "light 与 dark" in msg

    def test_low_contrast_warns_with_ratio(self):
        cfg = _theme_config.validate(color_foreground={"primary": "#0070F0"})
        assert any("对比度仅" in w for w in cfg["warnings"])


class TestRadius:
    def test_requires_all_three_and_order(self):
        assert "必须同时写 sm、md、lg" in _errors(radius={"sm": 2, "md": 4})
        assert "sm <= md <= lg" in _errors(radius={"sm": 10, "md": 6, "lg": 14})
        assert "非负整数" in _errors(radius={"sm": -1, "md": 2, "lg": 3})
        assert "非负整数" in _errors(radius={"sm": 1.5, "md": 2, "lg": 3})

    def test_valid(self):
        assert _theme_config.validate(radius={"sm": 0, "md": 0, "lg": 0})["radius"]["lg"] == 0


class TestSurfaces:
    def test_both_sides_required(self):
        assert "同时写 light 与 dark" in _errors(background={"light": "#FFFFFF"})
        assert "#RRGGBB" in _errors(foreground={"light": "#FFF", "dark": "#000000"})

    def test_layer_order_warns(self):
        cfg = _theme_config.validate(
            content_background={"light": "#101010", "dark": "#18181B"}
        )
        assert any("light 主题" in w for w in cfg["warnings"])


class TestFontSize:
    def test_valid_and_errors(self):
        ok = {"xs": 12, "sm": 14, "md": 16, "lg": 18, "xl": 20}
        assert _theme_config.validate(font_size=ok)["font_size"] == ok
        assert "五档" in _errors(font_size={"xs": 10, "sm": 13})
        assert "xs <= sm <= md <= lg <= xl" in _errors(
            font_size={"xs": 20, "sm": 13, "md": 16, "lg": 19, "xl": 22}
        )
        assert "8~28" in _errors(font_size={"xs": 4, "sm": 13, "md": 16, "lg": 19, "xl": 22})

    def test_base_size_is_md_shorthand(self):
        cfg = _theme_config.validate(font_base_size=18)
        assert cfg["font_size"]["md"] == 18 and cfg["font_size"]["sm"] == 13

    def test_base_size_conflict(self):
        msg = _errors(
            font_size={"xs": 10, "sm": 13, "md": 16, "lg": 19, "xl": 22}, font_base_size=18
        )
        assert "不一致" in msg

    def test_base_size_breaking_monotone_is_rejected(self):
        assert "xs <= sm" in _errors(font_base_size=9)  # md=9 < sm=13


class TestShadow:
    def _layer(self, **kw):
        base = {"y": 2, "blur": 10, "color": "#020304", "opacity": 0.06}
        base.update(kw)
        return base

    def _full(self, layers=None):
        layers = [self._layer()] if layers is None else layers
        side = {"sm": layers, "md": layers, "lg": layers}
        return {"light": side, "dark": side}

    def test_valid(self):
        cfg = _theme_config.validate(shadow=self._full())
        assert cfg["shadow"]["light"]["sm"][0].blur == 10.0

    def test_inset_flag(self):
        cfg = _theme_config.validate(shadow=self._full([self._layer(inset=True)]))
        assert cfg["shadow"]["dark"]["md"][0].inset is True

    def test_errors(self):
        assert "light 与 dark" in _errors(shadow={"light": {}})
        assert "三档" in _errors(shadow={"light": {"sm": []}, "dark": {"sm": []}})
        assert "1~4 层" in _errors(shadow=self._full([]))
        assert "opacity" in _errors(shadow=self._full([self._layer(opacity=2)]))
        assert "未知键" in _errors(shadow=self._full([self._layer(spread=3)]))


class TestFonts:
    def test_missing_font_name_and_file(self):
        assert "找不到字体" in _errors(font_family="这个字体不存在 XYZ")
        assert "字体文件不存在" in _errors(mono_family="D:/nope/missing.ttf")

    def test_empty_or_non_string(self):
        assert "非空字符串" in _errors(font_family="")
        assert "非空字符串" in _errors(mono_family=123)

    def test_bundled_font_by_name(self):
        cfg = _theme_config.validate(font_family="Source Han Sans CN VF")
        assert cfg["font_family"] == "Source Han Sans CN VF"


class TestSetupIntegration:
    def test_customised_setup_then_defaults_restore(self, qapp):
        HeroSideUIProvider.setup(
            qapp,
            filter_libpng_warnings=False,
            colors={"primary": ROSE},
            color_foreground={"primary": "#FEFEFF"},
            radius={"sm": 2, "md": 6, "lg": 10},
            font_size={"xs": 11, "sm": 14, "md": 17, "lg": 20, "xl": 24},
        )
        assert HEROUI_COLORS["primary"][500] == "#e11d48"
        assert RADIUS["lg"] == "10px"
        assert theme_values.get_font_px("md") == 17
        # 无参 setup：全部回到默认（幂等）
        HeroSideUIProvider.setup(qapp, filter_libpng_warnings=False)
        assert HEROUI_COLORS["primary"][500] == "#006FEE"
        assert RADIUS["lg"] == "14px"
        assert theme_values.get_font_px("md") == 16

    def test_invalid_setup_changes_nothing(self, qapp):
        HeroSideUIProvider.setup(qapp, filter_libpng_warnings=False)
        with pytest.raises(ValueError):
            HeroSideUIProvider.setup(
                qapp, filter_libpng_warnings=False, radius={"sm": 9, "md": 1, "lg": 2}
            )
        assert RADIUS["sm"] == "4px"

    def test_base_size_only_changes_md(self, qapp):
        HeroSideUIProvider.setup(qapp, filter_libpng_warnings=False, font_base_size=18)
        assert theme_values.get_font_sizes() == {"xs": 10, "sm": 13, "md": 18, "lg": 19, "xl": 22}

    def test_teardown_restores_theme_values(self, qapp):
        HeroSideUIProvider.setup(
            qapp, filter_libpng_warnings=False, radius={"sm": 1, "md": 2, "lg": 3}
        )
        HeroSideUIProvider.teardown()
        assert RADIUS["lg"] == "14px"

    def test_late_setup_warns_once_per_call(self, qapp):
        HeroSideUIProvider.setup(qapp, filter_libpng_warnings=False)
        theme_values.get_foreground("light")  # 模拟已有组件读取过主题取值
        with pytest.warns(UserWarning, match="组件创建之后"):
            HeroSideUIProvider.setup(
                qapp, filter_libpng_warnings=False, radius={"sm": 1, "md": 2, "lg": 3}
            )

    def test_setup_without_token_params_never_warns_late(self, qapp):
        HeroSideUIProvider.setup(qapp, filter_libpng_warnings=False)
        theme_values.get_foreground("light")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            HeroSideUIProvider.setup(qapp, filter_libpng_warnings=False)
        assert not [w for w in caught if "组件创建之后" in str(w.message)]

    def test_window_palette_uses_background_token(self, qapp):
        from PySide6.QtGui import QPalette

        HeroSideUIProvider.setup(
            qapp,
            theme="light",
            filter_libpng_warnings=False,
            background={"light": "#123456", "dark": "#0D0D0F"},
        )
        assert QApplication.palette().color(QPalette.ColorRole.Window).name() == "#123456"
        HeroSideUIProvider.teardown()
