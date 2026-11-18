"""color_foreground 的变体 / 状态 / 位置写法：取色规则、校验、提示、组件接入。

规则见 docs/foreground-variants-proposal.md。
"""

from __future__ import annotations

import pytest

from hero_side_ui import Button, DateInput, Input, InputOtp, Textarea
from hero_side_ui._shared.colors import build_chip_styles
from hero_side_ui.components.alert._styling import build_alert_styles
from hero_side_ui.components.calendar import _palette as calendar_palette
from hero_side_ui.components.pagination import _palette as pagination_palette
from hero_side_ui.components.toast._styling import build_toast_styles
from hero_side_ui.core import _theme_config
from hero_side_ui.core.state_palette import StatePalette
from hero_side_ui.themes import theme_values


@pytest.fixture(autouse=True)
def clean_theme_values():
    """每个测试前后把主题取值还原为默认值。"""
    theme_values.reset()
    theme_values.clear_read_flag()
    yield
    theme_values.reset()
    theme_values.clear_read_flag()


def _apply(**cfg) -> dict:
    out = _theme_config.validate(**cfg)
    theme_values.apply(out)
    return out


def _errors(**kwargs) -> str:
    with pytest.raises(ValueError) as exc:
        _theme_config.validate(**kwargs)
    return str(exc.value)


def _warns(**kwargs) -> list:
    return _theme_config.validate(**kwargs)["warnings"]


def _ov(color, theme, variant, **kw):
    return theme_values.foreground_override(color, theme, variant, **kw)


TREE = {
    "warning": {
        "light": {
            "default": "#010101",
            "solid": "#020202",
            "flat": {
                "default": "#030303",
                "hover": "#040404",
                "placeholder": "#050505",
            },
            "bordered": "#070707",
            "underlined": {"placeholder": "#080808", "label": "#090909"},
        },
        "dark": {"default": "#0a0a0a"},
    }
}


class TestDefaultsUnchanged:
    def test_no_config_means_no_override(self):
        assert _ov("warning", "light", "solid") is None
        assert _ov("primary", "dark", "flat", slot="icon") is None

    def test_get_color_foreground_keeps_defaults(self):
        assert theme_values.get_color_foreground("primary", "light") == "#FEFEFF"
        assert theme_values.get_color_foreground("warning", "dark") == "#11181C"
        assert theme_values.get_color_foreground("default", "dark") == "#D4D4D8"
        assert theme_values.get_color_foreground("foreground", "light") == "#FEFEFF"

    def test_reset_clears_user_set(self):
        _apply(color_foreground={"warning": "#112233"})
        assert theme_values.foreground_is_user_set("warning")
        theme_values.reset()
        assert not theme_values.foreground_is_user_set("warning")
        assert theme_values.get_color_foreground("warning", "light") == "#11181C"


class TestLegacyHex:
    """旧写法（单个 hex）的含义不变：只管 solid 与 ghost 悬停。"""

    def test_solid_and_ghost_hover(self):
        _apply(color_foreground={"primary": "#112233"})
        assert theme_values.get_color_foreground("primary", "light") == "#112233"
        assert theme_values.get_color_foreground("primary", "dark") == "#112233"
        assert _ov("primary", "light", "solid") == "#112233"
        assert _ov("primary", "light", "ghost", states="hover") == "#112233"

    def test_does_not_leak_to_other_variants_or_slots(self):
        _apply(color_foreground={"primary": "#112233"})
        assert _ov("primary", "light", "ghost") is None
        assert _ov("primary", "light", "flat") is None
        assert _ov("primary", "light", "solid", slot="description") is None
        assert _ov("primary", "light", "solid", slot="placeholder") is None

    def test_does_not_touch_disabled(self):
        _apply(color_foreground={"primary": "#112233"})
        assert _ov("primary", "light", "solid", states="disabled") is None

    def test_other_colors_stay_default(self):
        _apply(color_foreground={"primary": "#112233"})
        assert theme_values.get_color_foreground("danger", "light") == "#FEFEFF"
        assert _ov("danger", "light", "solid") is None


class TestResolutionOrder:
    @pytest.fixture(autouse=True)
    def _tree(self):
        _apply(color_foreground=TREE)

    def test_variant_hex_is_variant_default(self):
        assert _ov("warning", "light", "solid") == "#020202"
        assert _ov("warning", "light", "bordered") == "#070707"

    def test_get_color_foreground_reads_solid(self):
        assert theme_values.get_color_foreground("warning", "light") == "#020202"

    def test_variant_default_then_state_then_slot(self):
        assert _ov("warning", "light", "flat") == "#030303"
        assert _ov("warning", "light", "flat", states="hover") == "#040404"
        assert _ov("warning", "light", "flat", slot="placeholder") == "#050505"
        # 状态是 hex（= 状态的 default），没写位置时位置沿用变体里的
        assert _ov("warning", "light", "flat", states="hover", slot="placeholder") == "#050505"

    def test_theme_default_covers_text_icon_title_only(self):
        assert _ov("warning", "light", "faded") == "#010101"
        assert _ov("warning", "light", "faded", slot="icon") == "#010101"
        assert _ov("warning", "light", "faded", slot="title") == "#010101"
        for slot in ("label", "label_resting", "placeholder", "description"):
            assert _ov("warning", "light", "faded", slot=slot) is None

    def test_variant_without_default_falls_to_theme_default(self):
        assert _ov("warning", "light", "underlined") == "#010101"
        assert _ov("warning", "light", "underlined", slot="placeholder") == "#080808"

    def test_light_and_dark_are_independent(self):
        assert _ov("warning", "dark", "flat") == "#0a0a0a"
        assert _ov("warning", "dark", "flat", slot="label") is None
        assert theme_values.get_color_foreground("warning", "dark") == "#0a0a0a"

    def test_only_other_variants_keep_solid_default(self):
        _apply(color_foreground={"warning": {"light": {"flat": "#5B280A"}, "dark": "#11181C"}})
        assert theme_values.get_color_foreground("warning", "light") == "#11181C"
        assert _ov("warning", "light", "flat") == "#5B280A"


class TestStatePriority:
    @pytest.fixture(autouse=True)
    def _tree(self):
        _apply(
            color_foreground={
                "primary": {
                    "light": {
                        "flat": {
                            "hover": {"text": "#111111"},
                            "invalid": {"text": "#222222"},
                            "selected": {"text": "#333333"},
                            "disabled": {"text": "#444444"},
                        }
                    },
                    "dark": "#FEFEFF",
                }
            }
        )

    def _f(self, *states):
        return _ov("primary", "light", "flat", states=states)

    def test_single_state(self):
        assert self._f("hover") == "#111111"

    def test_priority_order(self):
        assert self._f("hover", "invalid") == "#222222"
        assert self._f("hover", "selected", "invalid") == "#222222"
        assert self._f("hover", "invalid", "disabled") == "#444444"

    def test_falls_to_next_state_when_missing(self):
        assert self._f("focus", "hover") == "#111111"

    def test_order_of_argument_does_not_matter(self):
        assert self._f("invalid", "hover") == self._f("hover", "invalid")


class TestDisabledDoesNotInherit:
    def test_disabled_ignores_variant_and_theme_default(self):
        _apply(color_foreground=TREE)
        assert _ov("warning", "light", "flat", states="disabled") is None
        assert _ov("warning", "light", "solid", states="disabled") is None

    def test_explicit_disabled_wins(self):
        _apply(
            color_foreground={
                "primary": {"light": {"flat": {"default": "#101010", "disabled": "#303030"}},
                            "dark": "#FEFEFF"}
            }
        )  # fmt: skip
        assert _ov("primary", "light", "flat", states="disabled") == "#303030"


class TestValidation:
    def test_missing_side(self):
        assert "light 与 dark" in _errors(color_foreground={"primary": {"light": "#FEFEFF"}})

    def test_unknown_variant_state_slot(self):
        msg = _errors(
            color_foreground={"primary": {"light": {"flatt": "#FEFEFF"}, "dark": "#FEFEFF"}}
        )
        assert "flatt" in msg
        msg = _errors(
            color_foreground={
                "primary": {"light": {"flat": {"hoverr": "#FEFEFF"}}, "dark": "#FEFEFF"}
            }
        )
        assert "hoverr" in msg

    def test_key_in_wrong_layer(self):
        msg = _errors(
            color_foreground={"primary": {"light": {"hover": "#FEFEFF"}, "dark": "#FEFEFF"}}
        )
        assert "状态名只能写在变体层" in msg
        msg = _errors(
            color_foreground={
                "primary": {"light": {"flat": {"flat": "#FEFEFF"}}, "dark": "#FEFEFF"}
            }
        )
        assert "变体名只能写在主题层" in msg
        msg = _errors(
            color_foreground={
                "primary": {"light": {"flat": {"hover": {"hover": "#FEFEFF"}}}, "dark": "#FEFEFF"}
            }
        )
        assert "状态名只能写在变体层或其下" in msg

    def test_empty_object(self):
        assert "空对象" in _errors(color_foreground={"primary": {"light": {}, "dark": "#FEFEFF"}})

    def test_not_hex(self):
        for bad in ("red", "#FFF", "rgb(1,2,3)", 5):
            msg = _errors(color_foreground={"primary": {"light": {"flat": bad}, "dark": "#FEFEFF"}})
            assert "#RRGGBB" in msg

    def test_slot_value_must_be_hex(self):
        msg = _errors(
            color_foreground={
                "primary": {"light": {"flat": {"text": {"a": "#FEFEFF"}}}, "dark": "#FEFEFF"}
            }
        )
        assert "必须是 #RRGGBB" in msg

    def test_all_problems_listed_together(self):
        msg = _errors(
            color_foreground={
                "primary": {"light": {"flat": "#zz"}, "dark": {"solid": "#FEFEFF", "x": "#FFFFFF"}}
            }
        )
        assert msg.count("\n  - ") >= 2

    def test_changed_ramp_still_requires_foreground(self):
        ramp = list(theme_values.DEFAULT_COLORS["primary"].values())
        ramp[5] = "#112233"
        assert "请同时在 color_foreground" in _errors(colors={"primary": ramp})

    def test_object_form_normalised(self):
        cfg = _theme_config.validate(color_foreground=TREE)
        assert cfg["color_foreground"]["warning"]["light"]["flat"]["hover"] == "#040404"


class TestWarnings:
    def test_good_config_is_quiet(self):
        w = _warns(
            color_foreground={
                "warning": {"light": {"solid": "#11181C", "flat": "#5B3A00"}, "dark": "#11181C"}
            }
        )
        assert w == []

    def test_low_contrast_on_flat(self):
        w = _warns(color_foreground={"warning": {"light": {"flat": "#FDD704"}, "dark": "#11181C"}})
        assert any(
            "浅底（flat）变体" in x and "对比度是 1.23" in x and "推荐 4.5 对比度" in x for x in w
        )

    def test_icon_needs_only_three(self):
        w = _warns(
            color_foreground={
                "primary": {"light": {"flat": {"icon": "#FEFEFF"}}, "dark": "#FEFEFF"}
            }
        )
        assert any("图标位置" in x and "推荐 3 对比度" in x for x in w)

    def test_theme_default_aggregates_into_one_warning(self):
        w = _warns(
            color_foreground={"warning": {"light": {"default": "#FEFEFF"}, "dark": "#11181C"}}
        )
        assert sum("配色对比度过低" in x for x in w) == 1

    def test_theme_default_skips_variants_written_explicitly(self):
        # 暗色的 default 是浅黄字：solid / shadow 单独写了深色字，就不该再按 default 警告
        w = _warns(
            color_foreground={
                "warning": {
                    "light": "#11181C",
                    "dark": {
                        "default": "#FFE08A",
                        "solid": "#11181C",
                        "shadow": "#11181C",
                        "ghost": {"hover": "#11181C"},
                    },
                }
            }
        )
        assert w == []
        # 只写 default 时，实色底上的浅黄字仍然要警告
        w = _warns(
            color_foreground={"warning": {"light": "#11181C", "dark": {"default": "#FFE08A"}}}
        )
        assert sum("配色对比度过低" in x for x in w) == 1

    def test_message_follows_title_and_description_format(self):
        w = _warns(
            color_foreground={"warning": {"light": "#11181C", "dark": {"default": "#FFE08A"}}}
        )
        assert len(w) == 1
        zh, en = w[0].split("\n")
        assert zh.startswith("有 1 处配色对比度过低：")
        assert "当前暗色模式下，warning 颜色 未单独设置的 solid、shadow 变体 正文位置" in zh
        assert "对比度是 1.58，推荐 4.5 对比度" in zh
        assert "In dark mode" in en and "recommended 4.5" in en
        # 不再出现内部词和路径
        assert (
            "default (" not in w[0]
            and "Button etc." not in w[0]
            and "color_foreground[" not in w[0]
        )

    def test_report_groups_by_theme_and_joins_with_semicolon(self):
        from hero_side_ui.core._foreground_config import (
            collect_foreground_issues,
            format_contrast_report,
        )

        out = _theme_config.validate(
            color_foreground={
                "warning": {
                    "light": {"flat": "#FDD704", "bordered": "#FDD704"},
                    "dark": {"flat": "#11181C"},
                }
            }
        )
        issues, unread = collect_foreground_issues(out["color_foreground"], out)
        assert unread == []
        title_zh, _title_en, desc_zh, _desc_en = format_contrast_report(issues)
        assert title_zh == f"有 {len(issues)} 处配色对比度过低"
        # 亮色两条用分号连，暗色另起一句
        assert desc_zh.count("当前亮色模式下，") == 1 and desc_zh.count("；") == 1
        assert desc_zh.count("当前暗色模式下，") == (
            1 if any(i.side == "dark" for i in issues) else 0
        )

    def test_disabled_not_checked(self):
        w = _warns(
            color_foreground={
                "warning": {"light": {"flat": {"disabled": "#fefefe"}}, "dark": "#11181C"}
            }
        )
        assert not any("配色对比度过低" in x for x in w)

    def test_only_unread_combinations_warn(self):
        # flat.hover：Button 读 -> 合法
        w = _warns(
            color_foreground={
                "warning": {"light": {"flat": {"hover": "#112233"}}, "dark": "#11181C"}
            }
        )
        assert not any("没有任何组件会读" in x for x in w)
        # underlined.hover：没有任何组件读 -> 警告
        w = _warns(
            color_foreground={
                "warning": {"light": {"underlined": {"hover": "#112233"}}, "dark": "#11181C"}
            }
        )
        assert any(
            "下划线（underlined）" in x and "悬停" in x and "没有任何组件会读" in x for x in w
        )

    def test_legacy_warnings_unchanged(self):
        assert any("对比度仅" in x for x in _warns(color_foreground={"primary": "#0070F0"}))
        assert _warns(color_foreground={"primary": "#FEFEFF"}) == []


FULL = {
    "primary": {
        "light": {
            "flat": {
                "default": "#101010",
                "hover": "#202020",
                "disabled": "#303030",
                "placeholder": "#404040",
                "label": "#505050",
                "label_resting": "#606060",
                "description": "#707070",
                "icon": "#808080",
                "invalid": {"text": "#909090"},
                "title": "#a0a0a0",
            },
            "bordered": "#b0b0b0",
            "solid": {"default": "#c0c0c0", "selected": {"text": "#222222"}},
        },
        "dark": {"default": "#d0d0d0"},
    }
}


class TestComponentsReadOverrides:
    @pytest.fixture(autouse=True)
    def _full(self):
        _apply(color_foreground=FULL)

    def test_button_text_states_and_icon(self, qtbot):
        b = Button("t", color="primary", variant="flat", theme="light")
        qtbot.addWidget(b)
        q = b.styleSheet()
        assert "color: #101010;" in q  # 普通
        assert "color: #202020;" in q  # 悬停
        assert "color: #303030;" in q  # 禁用
        assert b._resolve_icon_color() == "#808080"

    def test_button_variants_and_theme_default(self, qtbot):
        b = Button("t", color="primary", variant="bordered", theme="light")
        qtbot.addWidget(b)
        assert "color: #b0b0b0;" in b.styleSheet()
        b = Button("t", color="primary", variant="light", theme="dark")
        qtbot.addWidget(b)
        assert "color: #d0d0d0;" in b.styleSheet()

    def test_button_icon_follows_text_when_no_icon_configured(self, qtbot):
        b = Button("t", color="primary", variant="bordered", theme="light", icon_only=True)
        qtbot.addWidget(b)
        assert b._resolve_icon_color() == "#b0b0b0"

    def test_other_colors_untouched(self, qtbot):
        b = Button("t", color="danger", variant="flat", theme="light")
        qtbot.addWidget(b)
        assert "#101010" not in b.styleSheet()

    def test_chip_and_badge_tokens(self):
        flat = build_chip_styles("flat", "primary", "light")
        assert flat["fg"] == "#101010" and flat["close_color"] == "#808080"
        assert build_chip_styles("bordered", "primary", "light")["fg"] == "#b0b0b0"
        assert build_chip_styles("solid", "primary", "light")["fg"] == "#c0c0c0"

    def test_alert_tokens_and_close_follows_icon(self):
        t = build_alert_styles("flat", "primary", "light", "md")
        assert t["title_color"] == "#a0a0a0"
        assert t["desc_color"] == "#707070"
        assert t["icon_color"] == t["close_btn_color"] == "#808080"

    def test_toast_tokens_and_close_progress_follow_icon(self):
        t = build_toast_styles("flat", "primary", "light")
        assert t["title_color"] == "#a0a0a0" and t["desc_color"] == "#707070"
        assert t["icon_color"] == t["close_color"] == t["progress_color"] == "#808080"

    def test_input_slots(self, qtbot):
        i = Input(label="x", color="primary", variant="flat", theme="light", placeholder="p")
        qtbot.addWidget(i)
        assert "color: #101010;" in i.line_edit.styleSheet()
        assert i.line_edit.palette().placeholderText().color().name() == "#404040"
        assert i._label_color_floated.name() == "#505050"
        assert i._label_color_resting.name() == "#606060"

    def test_input_invalid_state(self, qtbot):
        i = Input(
            label="x", color="primary", variant="flat", theme="light",
            is_invalid=True, error_message="e",
        )  # fmt: skip
        qtbot.addWidget(i)
        assert "color: #909090;" in i.line_edit.styleSheet()

    def test_textarea_dateinput_otp(self, qtbot):
        ta = Textarea(label="x", color="primary", variant="flat", theme="light")
        qtbot.addWidget(ta)
        assert "#101010" in ta.text_edit.styleSheet()
        di = DateInput(label="x", color="primary", variant="flat", theme="light")
        qtbot.addWidget(di)
        assert di._label_color_floated.name() == "#505050"
        otp = InputOtp(length=4, color="primary", variant="flat", theme="light")
        qtbot.addWidget(otp)
        tok = otp._segment_styles()
        assert tok["text_filled"] == "#101010" and tok["text"] == "#404040"

    def test_list_rows_title_but_not_gray(self):
        assert StatePalette.text("flat", "primary", "light", "hover").name() == "#202020"
        assert StatePalette.text("flat", "primary", "light", "resting").name() == "#a0a0a0"
        assert StatePalette.text("flat", "default", "light", "hover").name() != "#202020"
        # solid 的普通行本来就是中性色，不读
        assert StatePalette.text("solid", "primary", "light", "resting").name() != "#c0c0c0"

    def test_table_selected_row_reads_flat_selected_title(self):
        from hero_side_ui.components.table import _palette as table_palette

        # FULL 里 flat 单独写了 title = #a0a0a0；选中行读 flat 的标题字色
        assert table_palette.selected_text("primary", "light").name() == "#a0a0a0"
        # 灰色不读
        assert table_palette.selected_text("default", "light").name() != "#a0a0a0"
        # 没配置时保持原色（primary 500）
        theme_values.reset()
        assert table_palette.selected_text("primary", "light").name() == "#006fee"

    def test_selected_state_for_solid_based_components(self):
        assert theme_values.get_color_foreground("primary", "light") == "#c0c0c0"
        assert theme_values.get_color_foreground("primary", "light", state="selected") == "#222222"
        assert calendar_palette.selected_text("primary", "light").name() == "#222222"
        assert pagination_palette.resolve_cursor_text("primary", "light").name() == "#222222"


class TestToastSuccess:
    def test_default_stays_dark(self):
        t = build_toast_styles("solid", "success", "light")
        assert t["title_color"] == theme_values.get_foreground("light")

    def test_follows_config_once_written(self):
        _apply(color_foreground={"success": "#FEFEFF"})
        t = build_toast_styles("solid", "success", "light")
        assert t["title_color"] == "#FEFEFF"
