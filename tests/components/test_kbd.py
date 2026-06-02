"""Kbd 组件单元测试。

覆盖维度：构造默认值、参数校验、keys/children/use_unicode 切换、
三档 size 像素驱动、五档 radius + size 推断、platform 路由、
主题切换（含 ThemeProvider 联动）、静态元信息。
"""

from __future__ import annotations

import pytest

from hero_side_ui import Kbd
from hero_side_ui.components.kbd._keys import (
    KBD_KEY_NAMES,
    KBD_KEYS_GLYPH_MAP,
    KBD_KEYS_LABEL_MAP,
    VALID_PLATFORMS,
    resolve_icon,
)
from hero_side_ui.components.kbd.kbd import DEFAULT_RADIUS_BY_SIZE, _KbdIconLabel
from hero_side_ui.components.text import Text
from hero_side_ui.themes import (
    KBD_SIZE_TABLE,
    VALID_KBD_RADII,
    VALID_KBD_SIZES,
)


# ------------------------------------------------------------
# 构造与默认值
# ------------------------------------------------------------
class TestKbdInit:
    def test_default(self, qtbot):
        w = Kbd()
        qtbot.addWidget(w)
        assert w._keys == []
        assert w._children_text == ""
        assert w._size == "md"
        assert w._radius == DEFAULT_RADIUS_BY_SIZE["md"]
        assert w._radius_explicit is False
        assert w._platform == "auto"
        assert w._theme_mode == "auto"
        assert w._use_unicode is False

    def test_children_only(self, qtbot):
        w = Kbd("Esc")
        qtbot.addWidget(w)
        assert w._children_text == "Esc"
        assert w._keys == []
        # 仅 children 时 slots 中应有一个 Text
        assert len(w._slots) == 1
        assert isinstance(w._slots[0], Text)

    def test_keys_str_normalize_to_list(self, qtbot):
        w = Kbd(keys="command")
        qtbot.addWidget(w)
        assert w._keys == ["command"]

    def test_keys_sequence_kept_in_order(self, qtbot):
        w = Kbd(keys=["command", "shift", "option"])
        qtbot.addWidget(w)
        assert w._keys == ["command", "shift", "option"]

    def test_keys_plus_children_slot_count(self, qtbot):
        w = Kbd("N", keys=["command", "shift"])
        qtbot.addWidget(w)
        # 2 个 key + 1 个 children = 3 个 slot
        assert len(w._slots) == 3

    def test_unknown_key_falls_back_to_text(self, qtbot):
        # 未注册 key：resolve_icon 返回 None → 走 Text(glyph fallback)
        w = Kbd(keys="totally-not-a-key")
        qtbot.addWidget(w)
        assert len(w._slots) == 1
        assert isinstance(w._slots[0], Text)


# ------------------------------------------------------------
# 参数校验
# ------------------------------------------------------------
class TestKbdValidation:
    def test_invalid_size_raises(self, qtbot):
        with pytest.raises(ValueError):
            Kbd(size="xl")

    def test_invalid_radius_raises(self, qtbot):
        with pytest.raises(ValueError):
            Kbd(radius="huge")

    def test_invalid_platform_raises(self, qtbot):
        with pytest.raises(ValueError):
            Kbd(platform="android")


# ------------------------------------------------------------
# keys / children / use_unicode setter
# ------------------------------------------------------------
class TestKbdKeysAndChildren:
    def test_set_keys_none_clears(self, qtbot):
        w = Kbd(keys="command")
        qtbot.addWidget(w)
        w.set_keys(None)
        assert w.keys() == []
        assert w._slots == []

    def test_set_keys_replaces_slots(self, qtbot):
        w = Kbd(keys=["command"])
        qtbot.addWidget(w)
        w.set_keys(["shift", "option"])
        assert w.keys() == ["shift", "option"]
        assert len(w._slots) == 2

    def test_keys_returns_copy(self, qtbot):
        w = Kbd(keys=["command", "shift"])
        qtbot.addWidget(w)
        out = w.keys()
        out.append("ctrl")  # 不应影响内部
        assert w.keys() == ["command", "shift"]

    def test_set_children_appends_text_slot(self, qtbot):
        w = Kbd(keys="command")
        qtbot.addWidget(w)
        w.set_children("K")
        assert w.children_text() == "K"
        assert len(w._slots) == 2  # icon + text

    def test_set_children_empty_removes_text_slot(self, qtbot):
        w = Kbd("K", keys="command")
        qtbot.addWidget(w)
        w.set_children("")
        assert w.children_text() == ""
        assert len(w._slots) == 1


class TestKbdUnicodeMode:
    """use_unicode=True 时所有 keys 走 Text 字符渲染，不再使用 _KbdIconLabel。"""

    def test_default_uses_svg_label(self, qtbot):
        w = Kbd(keys="command")  # mac/win 都有 icon
        qtbot.addWidget(w)
        assert isinstance(w._slots[0], _KbdIconLabel)

    def test_use_unicode_routes_to_text(self, qtbot):
        w = Kbd(keys="command", use_unicode=True)
        qtbot.addWidget(w)
        assert isinstance(w._slots[0], Text)
        # 内容应为 unicode glyph
        assert KBD_KEYS_GLYPH_MAP["command"] in w._slots[0].text()

    def test_set_use_unicode_toggle(self, qtbot):
        w = Kbd(keys="command")
        qtbot.addWidget(w)
        assert isinstance(w._slots[0], _KbdIconLabel)
        w.set_use_unicode(True)
        assert isinstance(w._slots[0], Text)
        w.set_use_unicode(False)
        assert isinstance(w._slots[0], _KbdIconLabel)

    def test_set_use_unicode_idempotent(self, qtbot):
        w = Kbd(keys="command", use_unicode=True)
        qtbot.addWidget(w)
        first = w._slots[0]
        w.set_use_unicode(True)  # 同值 no-op
        assert w._slots[0] is first


# ------------------------------------------------------------
# size
# ------------------------------------------------------------
class TestKbdSizes:
    @pytest.mark.parametrize("size", VALID_KBD_SIZES)
    def test_all_sizes_construct(self, qtbot, size):
        w = Kbd(keys="command", size=size)
        qtbot.addWidget(w)
        assert w._size == size

    @pytest.mark.parametrize("size", VALID_KBD_SIZES)
    def test_min_height_matches_table(self, qtbot, size):
        w = Kbd(size=size)
        qtbot.addWidget(w)
        assert w.minimumHeight() == KBD_SIZE_TABLE[size]["min_height"]

    def test_set_size_updates_min_height(self, qtbot):
        w = Kbd(size="sm")
        qtbot.addWidget(w)
        w.set_size("lg")
        assert w._size == "lg"
        assert w.minimumHeight() == KBD_SIZE_TABLE["lg"]["min_height"]

    def test_set_size_idempotent(self, qtbot):
        w = Kbd(size="md")
        qtbot.addWidget(w)
        w.set_size("md")  # 同值不抛
        assert w._size == "md"

    def test_set_size_reinfers_radius_when_implicit(self, qtbot):
        # 未显式传 radius，size 切换时 radius 应跟着推断
        w = Kbd(size="sm")
        qtbot.addWidget(w)
        assert w._radius_explicit is False
        w.set_size("lg")
        assert w._radius == DEFAULT_RADIUS_BY_SIZE["lg"]

    def test_set_size_keeps_explicit_radius(self, qtbot):
        # 显式传 radius，size 切换时不动
        w = Kbd(size="sm", radius="none")
        qtbot.addWidget(w)
        assert w._radius_explicit is True
        w.set_size("lg")
        assert w._radius == "none"


# ------------------------------------------------------------
# radius
# ------------------------------------------------------------
class TestKbdRadius:
    @pytest.mark.parametrize("radius", VALID_KBD_RADII)
    def test_all_radii_construct(self, qtbot, radius):
        w = Kbd(keys="command", radius=radius)
        qtbot.addWidget(w)
        assert w._radius == radius
        assert w._radius_explicit is True

    def test_default_radius_inferred_from_size(self, qtbot):
        for size in VALID_KBD_SIZES:
            w = Kbd(size=size)
            qtbot.addWidget(w)
            assert w._radius == DEFAULT_RADIUS_BY_SIZE[size]
            assert w._radius_explicit is False

    def test_set_radius_value(self, qtbot):
        w = Kbd()
        qtbot.addWidget(w)
        w.set_radius("full")
        assert w._radius == "full"
        assert w._radius_explicit is True

    def test_set_radius_none_returns_to_inferred(self, qtbot):
        w = Kbd(size="sm", radius="full")
        qtbot.addWidget(w)
        assert w._radius_explicit is True
        w.set_radius(None)
        assert w._radius_explicit is False
        assert w._radius == DEFAULT_RADIUS_BY_SIZE["sm"]

    def test_set_radius_idempotent(self, qtbot):
        w = Kbd(radius="md")
        qtbot.addWidget(w)
        w.set_radius("md")  # 同值不抛
        assert w._radius == "md"

    def test_radius_pixel_in_qss(self, qtbot):
        # 显式 sm + size=md → 表内 3px
        w = Kbd(size="md", radius="sm")
        qtbot.addWidget(w)
        expected = KBD_SIZE_TABLE["md"]["radius"]["sm"]
        assert f"border-radius: {expected}px" in w.styleSheet()

    def test_radius_full_uses_half_height(self, qtbot):
        # full 走 min_height // 2
        w = Kbd(size="md", radius="full")
        qtbot.addWidget(w)
        half = KBD_SIZE_TABLE["md"]["min_height"] // 2
        assert f"border-radius: {half}px" in w.styleSheet()


# ------------------------------------------------------------
# platform 路由（fn / alt）
# ------------------------------------------------------------
class TestKbdPlatform:
    def test_fn_mac_globe(self):
        assert resolve_icon("fn", "mac") == "ion--globe-outline"

    def test_fn_win_function(self):
        assert resolve_icon("fn", "win") == "tabler--function"

    def test_alt_mac_option(self):
        # mac 上 alt 用 mac-option 图标
        assert resolve_icon("alt", "mac") == "carbon--mac-option"

    def test_alt_win(self):
        assert resolve_icon("alt", "win") == "tabler--alt"

    def test_common_key_ignores_platform(self):
        # 非平台敏感 key：mac/win 一致
        assert resolve_icon("command", "mac") == resolve_icon("command", "win")

    def test_unknown_platform_falls_back_to_auto(self):
        # 非法 platform 字符串 → resolve_icon 走 _detect_platform 兜底，不应抛
        assert resolve_icon("command", "garbage") is not None

    def test_set_platform_rebuilds_slots(self, qtbot):
        # 强制 mac/win 切换：fn 的 icon name 应不同
        w = Kbd(keys="fn", platform="mac")
        qtbot.addWidget(w)
        assert isinstance(w._slots[0], _KbdIconLabel)
        mac_name = w._slots[0]._icon_name
        w.set_platform("win")
        assert w._slots[0]._icon_name != mac_name

    def test_set_platform_idempotent(self, qtbot):
        w = Kbd(keys="fn", platform="mac")
        qtbot.addWidget(w)
        w.set_platform("mac")  # 同值不抛
        assert w._platform == "mac"


# ------------------------------------------------------------
# 主题
# ------------------------------------------------------------
class TestKbdTheme:
    def test_fixed_light(self, qtbot):
        w = Kbd(theme="light")
        qtbot.addWidget(w)
        assert w._theme == "light"
        assert w._theme_mode == "light"

    def test_fixed_dark(self, qtbot):
        w = Kbd(theme="dark")
        qtbot.addWidget(w)
        assert w._theme == "dark"

    def test_set_theme_to_dark(self, qtbot):
        w = Kbd(theme="light")
        qtbot.addWidget(w)
        w.set_theme("dark")
        assert w._theme == "dark"

    def test_set_theme_back_to_auto(self, qtbot):
        w = Kbd(theme="dark")
        qtbot.addWidget(w)
        w.set_theme("auto")
        assert w._theme_mode == "auto"

    def test_auto_follows_provider_toggle(self, qtbot):
        from hero_side_ui import ThemeProvider

        ThemeProvider._reset_for_test()
        provider = ThemeProvider.instance()
        provider.set_mode("light")

        w = Kbd(theme="auto")
        qtbot.addWidget(w)
        assert w._theme == "light"

        provider.toggle()
        assert w._theme == "dark"

        ThemeProvider._reset_for_test()

    def test_fixed_theme_ignores_provider_toggle(self, qtbot):
        from hero_side_ui import ThemeProvider

        ThemeProvider._reset_for_test()
        provider = ThemeProvider.instance()
        provider.set_mode("light")

        w = Kbd(theme="dark")  # 固定 dark
        qtbot.addWidget(w)
        provider.toggle()
        assert w._theme == "dark"  # 不受 provider 影响

        ThemeProvider._reset_for_test()


# ------------------------------------------------------------
# 静态元信息
# ------------------------------------------------------------
class TestKbdMeta:
    def test_valid_keys_returns_full_set(self):
        assert Kbd.valid_keys() == KBD_KEY_NAMES
        # 全部 key 都有 label / glyph 兜底
        for k in Kbd.valid_keys():
            assert k in KBD_KEYS_LABEL_MAP
            assert k in KBD_KEYS_GLYPH_MAP

    def test_valid_sizes(self):
        assert Kbd.valid_sizes() == VALID_KBD_SIZES

    def test_valid_radii_includes_full(self):
        assert "full" in Kbd.valid_radii()
        assert Kbd.valid_radii() == VALID_KBD_RADII

    def test_valid_platforms(self):
        assert Kbd.valid_platforms() == VALID_PLATFORMS
        assert "auto" in Kbd.valid_platforms()
