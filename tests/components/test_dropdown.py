"""Dropdown 组件测试"""

from PySide6.QtWidgets import QAbstractButton, QWidget

from hero_side_ui import (
    Dropdown,
    DropdownItem,
    DropdownSection,
    ListboxItem,
    ListboxSection,
    StatePalette,
)
from hero_side_ui.components.button import Button
from hero_side_ui.themes import DROPDOWN_SIZES


# ============================================================
# 初始化
# ============================================================
class TestDropdownInit:
    def test_default_params(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        assert dd._selection_mode == "none"
        assert dd._close_on_select is True
        assert dd._placement == "bottom"
        assert dd._variant == "solid"
        assert dd._color == "default"
        assert dd._size == "md"
        assert dd._radius == "md"
        assert dd._theme_mode == "auto"
        assert dd.is_open() is False
        assert dd.is_disabled() is False
        assert dd._is_disabled is False

    def test_default_trigger_created(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        assert dd._owns_trigger is True
        assert dd.trigger_widget() is not None
        assert isinstance(dd.trigger_widget(), QAbstractButton)

    def test_custom_trigger(self, qtbot):
        btn = Button("Actions")
        dd = Dropdown(trigger=btn)
        qtbot.addWidget(dd)
        assert dd.trigger_widget() is btn
        assert dd._owns_trigger is False

    def test_items_from_tuple(self, qtbot):
        dd = Dropdown(items=[("new", "New file"), ("open", "Open")])
        qtbot.addWidget(dd)
        assert len(dd.items()) == 2
        assert dd.item_by_key("new").title() == "New file"

    def test_items_from_str(self, qtbot):
        dd = Dropdown(items=["Copy", "Paste"])
        qtbot.addWidget(dd)
        assert dd.item_by_key("Copy") is not None
        assert dd.items()[0].title() == "Copy"

    def test_items_from_dict(self, qtbot):
        dd = Dropdown(
            items=[
                {
                    "key": "del",
                    "label": "Delete",
                    "description": "remove it",
                    "shortcut": "Del",
                    "color": "danger",
                }
            ]
        )
        qtbot.addWidget(dd)
        it = dd.item_by_key("del")
        assert it.title() == "Delete"
        assert it.description() == "remove it"
        assert it.shortcut_text() == "Del"
        assert dd._item_colors == {"del": "danger"}

    def test_items_from_dropdown_item(self, qtbot):
        it = DropdownItem("Rename", key="rename")
        dd = Dropdown(items=[it])
        qtbot.addWidget(dd)
        assert dd.items()[0] is it

    def test_radius_applied_to_menu_at_construction(self, qtbot):
        dd = Dropdown(items=[("a", "A")], radius="full")
        qtbot.addWidget(dd)
        assert dd._listbox._radius == "full"

    def test_invalid_params_fallback(self, qtbot):
        dd = Dropdown(
            placement="nowhere",
            variant="invalid",
            color="nope",
            size="huge",
            radius="xl",
            selection_mode="weird",
        )
        qtbot.addWidget(dd)
        assert dd._placement == "bottom"
        assert dd._variant == "solid"
        assert dd._color == "default"
        assert dd._size == "md"
        assert dd._radius == "md"
        assert dd._selection_mode == "none"

    def test_initial_selected_keys_collapse_in_single(self, qtbot):
        dd = Dropdown(
            items=[("a", "A"), ("b", "B")],
            selection_mode="single",
            selected_keys={"a", "b"},
        )
        qtbot.addWidget(dd)
        assert len(dd.selected_keys()) == 1


# ============================================================
# Items 装配
# ============================================================
class TestDropdownItems:
    def test_set_items_replaces_old(self, qtbot):
        dd = Dropdown(items=[("a", "A")])
        qtbot.addWidget(dd)
        dd.set_items([("b", "B"), ("c", "C")])
        assert len(dd.items()) == 2
        assert dd.item_by_key("a") is None

    def test_set_items_clears_color_overrides(self, qtbot):
        dd = Dropdown(items=[{"key": "a", "label": "A", "color": "danger"}])
        qtbot.addWidget(dd)
        assert dd._item_colors == {"a": "danger"}
        dd.set_items([("b", "B")])
        assert dd._item_colors == {}

    def test_per_item_close_on_select_recorded(self, qtbot):
        dd = Dropdown(
            items=[
                {"key": "keep", "label": "Keep open", "close_on_select": False},
                {"key": "close", "label": "Close"},
            ]
        )
        qtbot.addWidget(dd)
        assert dd._item_close_on_select == {"keep": False}
        assert dd._should_close_on_select("keep") is False
        assert dd._should_close_on_select("close") is True

    def test_invalid_item_color_ignored(self, qtbot):
        dd = Dropdown(items=[{"key": "a", "label": "A", "color": "not-a-color"}])
        qtbot.addWidget(dd)
        assert dd._item_colors == {}

    def test_add_section_via_menu(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        sec = dd.add_section("Group", show_divider=True)
        sec.add_item("Inside", key="inside")
        assert len(dd.menu()._sections) == 1
        assert isinstance(sec, ListboxSection)
        assert sec.items()[0].key() == "inside"

    def test_add_item_with_color(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        it = dd.add_item("Delete", key="del", color="danger")
        assert dd.item_by_key("del") is it
        # add_item 支持 Listbox 没有的 color，并立刻下发到该项
        assert dd._item_colors == {"del": "danger"}
        assert it._color == "danger"

    def test_add_item_with_close_on_select(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.add_item("Pin", key="pin", close_on_select=False)
        assert dd._should_close_on_select("pin") is False

    def test_add_item_with_dict(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.add_item({"key": "a", "label": "A", "shortcut": "Ctrl+A"})
        assert dd.item_by_key("a").shortcut_text() == "Ctrl+A"

    def test_add_item_without_key_uses_title(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        it = dd.add_item("Plain")
        assert it.key() == "Plain"


# ============================================================
# 动作与关闭
# ============================================================
class TestDropdownAction:
    def _make(self, qtbot, **kw):
        dd = Dropdown(items=[("a", "A"), ("b", "B")], **kw)
        qtbot.addWidget(dd)
        return dd

    def test_action_signal(self, qtbot):
        dd = self._make(qtbot)
        with qtbot.waitSignal(dd.action, timeout=200) as blocker:
            dd.item_by_key("b").activated.emit("b")
        assert blocker.args == ["b"]

    def test_close_on_select_default(self, qtbot):
        dd = self._make(qtbot)
        calls = []
        dd._is_open = True
        dd.close = lambda: calls.append("close")
        dd._on_action("a")
        assert calls == ["close"]

    def test_close_on_select_false(self, qtbot):
        dd = self._make(qtbot, close_on_select=False)
        calls = []
        dd._is_open = True
        dd.close = lambda: calls.append("close")
        dd._on_action("a")
        assert calls == []

    def test_per_item_close_on_select_overrides_global(self, qtbot):
        dd = self._make(qtbot, close_on_select=True)
        dd._item_close_on_select["a"] = False
        calls = []
        dd._is_open = True
        dd.close = lambda: calls.append("close")
        dd._on_action("a")
        assert calls == []
        dd._on_action("b")
        assert calls == ["close"]

    def test_set_close_on_select(self, qtbot):
        dd = self._make(qtbot)
        dd.set_close_on_select(False)
        assert dd._should_close_on_select("a") is False
        dd.set_close_on_select(True)
        assert dd._should_close_on_select("a") is True


# ============================================================
# 选中
# ============================================================
class TestDropdownSelection:
    def test_none_mode_ignores_selection(self, qtbot):
        dd = Dropdown(items=[("a", "A"), ("b", "B")])
        qtbot.addWidget(dd)
        dd.set_selected_keys({"a"})
        assert dd.selected_keys() == set()
        assert dd.selected_key() is None

    def test_single_payload_is_key(self, qtbot):
        dd = Dropdown(items=[("a", "A"), ("b", "B")], selection_mode="single")
        qtbot.addWidget(dd)
        with qtbot.waitSignal(dd.selection_changed, timeout=200) as blocker:
            dd.set_selected_keys({"b"})
        assert blocker.args == ["b"]
        assert dd.selected_key() == "b"

    def test_multiple_payload_is_set(self, qtbot):
        dd = Dropdown(
            items=[("a", "A"), ("b", "B")],
            selection_mode="multiple",
            default_selected_keys={"a"},
        )
        qtbot.addWidget(dd)
        with qtbot.waitSignal(dd.selection_changed, timeout=200) as blocker:
            dd.set_selected_keys({"a", "b"})
        assert blocker.args == [{"a", "b"}]

    def test_action_still_emits_in_selection_mode(self, qtbot):
        dd = Dropdown(items=[("a", "A")], selection_mode="single")
        qtbot.addWidget(dd)
        with qtbot.waitSignal(dd.action, timeout=200) as blocker:
            dd.item_by_key("a").activated.emit("a")
        assert blocker.args == ["a"]

    def test_set_selection_mode_to_none_clears(self, qtbot):
        dd = Dropdown(
            items=[("a", "A"), ("b", "B")],
            selection_mode="single",
            selected_keys={"a"},
        )
        qtbot.addWidget(dd)
        dd.set_selection_mode("none")
        assert dd.selection_mode() == "none"
        assert dd.selected_keys() == set()

    def test_set_selection_mode_single_collapses(self, qtbot):
        dd = Dropdown(
            items=[("a", "A"), ("b", "B")],
            selection_mode="multiple",
            selected_keys={"a", "b"},
        )
        qtbot.addWidget(dd)
        dd.set_selection_mode("single")
        assert len(dd.selected_keys()) == 1

    def test_set_selection_mode_invalid_ignored(self, qtbot):
        dd = Dropdown(items=[("a", "A")], selection_mode="single")
        qtbot.addWidget(dd)
        dd.set_selection_mode("weird")
        assert dd.selection_mode() == "single"

    def test_disallow_empty_selection_passthrough(self, qtbot):
        dd = Dropdown(items=[("a", "A")], selection_mode="multiple")
        qtbot.addWidget(dd)
        dd.set_disallow_empty_selection(True)
        assert dd._listbox.disallow_empty_selection() is True


# ============================================================
# 禁用
# ============================================================
class TestDropdownDisabled:
    def test_disabled_keys_passthrough(self, qtbot):
        dd = Dropdown(items=[("a", "A"), ("b", "B")], disabled_keys={"b"})
        qtbot.addWidget(dd)
        assert dd._listbox._disabled_keys == {"b"}
        assert dd.item_by_key("b").is_disabled() is True

    def test_set_disabled_keys(self, qtbot):
        dd = Dropdown(items=[("a", "A"), ("b", "B")])
        qtbot.addWidget(dd)
        dd.set_disabled_keys({"a"})
        assert dd._listbox._disabled_keys == {"a"}

    def test_set_is_disabled_disables_trigger(self, qtbot):
        dd = Dropdown(items=[("a", "A")])
        qtbot.addWidget(dd)
        dd.set_is_disabled(True)
        assert dd.is_disabled() is True
        assert dd.trigger_widget().isEnabled() is False

    def test_open_blocked_when_disabled(self, qtbot):
        dd = Dropdown(items=[("a", "A")], disable_animation=True)
        qtbot.addWidget(dd)
        dd.set_is_disabled(True)
        dd.open()
        assert dd.is_open() is False

    def test_disabling_closes_open_menu(self, qtbot):
        dd = Dropdown(items=[("a", "A")], disable_animation=True)
        qtbot.addWidget(dd)
        dd._is_open = True
        calls = []
        dd._popover.close = lambda: calls.append("close")
        dd.set_is_disabled(True)
        assert calls == ["close"]


# ============================================================
# 开合
# ============================================================
class TestDropdownOpenClose:
    def test_is_open_state_via_open_changed(self, qtbot):
        dd = Dropdown(items=[("a", "A")])
        qtbot.addWidget(dd)
        assert dd.is_open() is False
        dd._on_open_changed(True)
        assert dd.is_open() is True
        # Esc 只在菜单打开时接管
        assert dd._esc.isEnabled() is True
        dd._on_open_changed(False)
        assert dd.is_open() is False
        assert dd._esc.isEnabled() is False

    def test_open_changed_signal(self, qtbot):
        dd = Dropdown(items=[("a", "A")])
        qtbot.addWidget(dd)
        with qtbot.waitSignal(dd.opened, timeout=200):
            dd._on_open_changed(True)
        with qtbot.waitSignal(dd.closed, timeout=200):
            dd._on_open_changed(False)

    def test_toggle(self, qtbot):
        dd = Dropdown(items=[("a", "A")], disable_animation=True)
        qtbot.addWidget(dd)
        calls = []
        orig_open, orig_close = dd.open, dd.close
        dd.open = lambda: calls.append("open")
        dd.close = lambda: calls.append("close")

        assert dd._is_open is False
        dd.toggle()
        assert calls == ["open"]

        calls.clear()
        dd._is_open = True
        dd.toggle()
        assert calls == ["close"]

        dd.open, dd.close = orig_open, orig_close

    def test_popover_open_close(self, qtbot):
        dd = Dropdown(items=[("a", "A")], disable_animation=True)
        qtbot.addWidget(dd)
        qtbot.addWidget(dd._popover)
        dd.show()
        qtbot.waitExposed(dd)
        dd.open()
        qtbot.waitUntil(lambda: dd._popover.is_open() is True, timeout=2000)
        qtbot.waitUntil(lambda: dd.is_open() is True, timeout=2000)
        dd.close()
        qtbot.waitUntil(lambda: dd._popover.is_open() is False, timeout=2000)


# ============================================================
# Trigger
# ============================================================
class TestDropdownTrigger:
    def test_button_trigger_uses_clicked(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        assert dd._trigger_click_connected is True

    def test_plain_widget_trigger_uses_event_filter(self, qtbot):
        host = QWidget()
        dd = Dropdown(trigger=host)
        qtbot.addWidget(dd)
        assert dd._trigger_click_connected is False

    def test_set_trigger_replaces_and_frees_old(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        old = dd.trigger_widget()
        new = Button("New")
        dd.set_trigger(new)
        assert dd.trigger_widget() is new
        assert dd._owns_trigger is False
        # 旧 trigger 出布局并被 safe_delete 隐藏（销毁是 deleteLater 延迟的）
        assert dd._outer.indexOf(new) >= 0
        assert dd._outer.indexOf(old) == -1
        assert old.isHidden() is True

    def test_set_trigger_same_widget_noop(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        old = dd.trigger_widget()
        dd.set_trigger(old)
        assert dd.trigger_widget() is old

    def test_set_trigger_none_noop(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        old = dd.trigger_widget()
        dd.set_trigger(None)
        assert dd.trigger_widget() is old


# ============================================================
# 几何
# ============================================================
class TestDropdownGeometry:
    def test_menu_min_width_from_size(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        assert dd._menu_min_width() == DROPDOWN_SIZES["md"]["menu_min_width"]

    def test_menu_min_width_override(self, qtbot):
        dd = Dropdown(min_width=320)
        qtbot.addWidget(dd)
        assert dd._menu_min_width() == 320
        dd.set_min_width(180)
        assert dd._menu_min_width() == 180

    def test_menu_max_height_override(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        # 默认不设上限：高度完全由内容撑开
        assert dd._menu_max_height() is None
        dd.set_max_height(120)
        assert dd._menu_max_height() == 120

    def test_menu_width_follows_trigger(self, qtbot):
        dd = Dropdown(items=[("a", "A")])
        qtbot.addWidget(dd)
        dd.show()
        dd._refresh_menu_width()
        expected = max(dd._trigger.width(), dd._menu_min_width())
        assert dd._scroll.minimumWidth() == expected

    def test_menu_height_capped_by_max_height(self, qtbot):
        dd = Dropdown(items=[(str(i), f"Item {i}") for i in range(30)], max_height=120)
        qtbot.addWidget(dd)
        dd._refresh_menu_height()
        # 传了 max_height 就固定在该高度，内容更高时滚动
        assert dd._scroll.maximumHeight() == 120
        assert dd._scroll.minimumHeight() == 120

    def test_menu_height_hugs_content(self, qtbot):
        # 菜单高度紧贴内容；上下限锁成同一个值，避免被缓存的 sizeHint 撑高
        dd = Dropdown(items=[("a", "A"), ("b", "B"), ("c", "C")])
        qtbot.addWidget(dd)
        dd._refresh_menu_height()
        assert dd._scroll.minimumHeight() == dd._visible_menu_height()
        assert dd._scroll.maximumHeight() == dd._scroll.minimumHeight()

    def test_menu_height_uncapped_by_default(self, qtbot):
        # 不传 max_height 时不会被 size token 截断
        dd = Dropdown(items=[(str(i), f"Item {i}") for i in range(40)])
        qtbot.addWidget(dd)
        dd._refresh_menu_height()
        assert dd._scroll.minimumHeight() > DROPDOWN_SIZES["md"]["popover_max_height"]
        assert dd._scroll.maximumHeight() == dd._scroll.minimumHeight()

    def _open_and_settle(self, qtbot, dd):
        dd.show()
        qtbot.addWidget(dd._popover)
        qtbot.waitExposed(dd)
        dd.open()
        qtbot.waitUntil(lambda: dd.is_open() is True, timeout=2000)
        qtbot.wait(80)

    def test_visible_menu_height_stable_after_show(self, qtbot):
        # 内容高度不能因为 show 过一次就变（首开 / 再开必须一致）
        dd = Dropdown(items=[(str(i), f"Item {i}") for i in range(8)])
        qtbot.addWidget(dd)
        before = dd._visible_menu_height()
        dd.show()
        qtbot.waitExposed(dd)
        qtbot.wait(30)
        assert dd._visible_menu_height() == before

    def test_max_height_kept_on_reopen(self, qtbot):
        # 传了 max_height 后，每次打开都要生效（不能只有首开受限）
        dd = Dropdown(
            items=[(str(i), f"Item {i}") for i in range(30)],
            max_height=120,
            disable_animation=True,
        )
        qtbot.addWidget(dd)
        self._open_and_settle(qtbot, dd)
        assert dd._scroll.minimumHeight() == 120
        dd.close()
        qtbot.waitUntil(lambda: dd.is_open() is False, timeout=2000)
        dd.open()
        qtbot.waitUntil(lambda: dd.is_open() is True, timeout=2000)
        qtbot.wait(80)
        assert dd._scroll.minimumHeight() == 120
        assert dd._scroll.maximumHeight() == 120

    def test_content_height_kept_on_reopen(self, qtbot):
        # 不传 max_height 时紧贴内容，重复打开高度不变
        dd = Dropdown(items=[("a", "A"), ("b", "B"), ("c", "C")], disable_animation=True)
        qtbot.addWidget(dd)
        self._open_and_settle(qtbot, dd)
        first = dd._scroll.minimumHeight()
        dd.close()
        qtbot.waitUntil(lambda: dd.is_open() is False, timeout=2000)
        dd.open()
        qtbot.waitUntil(lambda: dd.is_open() is True, timeout=2000)
        qtbot.wait(80)
        assert dd._scroll.minimumHeight() == first
        assert dd._scroll.maximumHeight() == first

    def test_dark_hover_differs_from_popover_bg(self, qtbot):
        # 暗色下 hover 底色不能和浮层底色撞色（历史 bug：两者都是 #27272a → 看不见）
        for variant in ("solid", "shadow", "flat", "faded"):
            dd = Dropdown(items=[("a", "A"), ("b", "B")], variant=variant, theme="dark")
            qtbot.addWidget(dd)
            pop_bg = dd._popover.current_bg_color()
            hover = StatePalette.bg(variant, dd._color, dd._theme, "hover")
            if hover.alpha() == 0:
                continue  # bordered / light 靠 border 或字色区分，不铺底
            assert hover.name() != pop_bg.name(), (
                f"{variant} hover {hover.name()} 与浮层底 {pop_bg.name()} 同色"
            )

    def test_popover_radius_full_falls_back_to_lg(self, qtbot):
        # full 只作用于菜单项，浮层退化为 lg
        dd = Dropdown(items=[("a", "A")], radius="full")
        qtbot.addWidget(dd)
        assert dd._popover._radius == "lg"
        assert dd._listbox._radius == "full"
        dd.set_radius("none")
        assert dd._popover._radius == "none"


# ============================================================
# Setter
# ============================================================
class TestDropdownSetters:
    def test_set_variant(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.set_variant("flat")
        assert dd._variant == "flat"
        assert dd._listbox._variant == "flat"

    def test_set_invalid_variant_ignored(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.set_variant("nope")
        assert dd._variant == "solid"

    def test_trigger_variant_falls_back_for_shadow(self, qtbot):
        # shadow 是菜单（Listbox）专属变体，Button 触发器回落到 solid
        dd = Dropdown(items=[("a", "A")], variant="shadow")
        qtbot.addWidget(dd)
        assert dd._variant == "shadow"
        assert dd._listbox._variant == "shadow"
        assert dd.trigger_widget()._variant == "solid"

    def test_set_variant_syncs_trigger(self, qtbot):
        dd = Dropdown(items=[("a", "A")])
        qtbot.addWidget(dd)
        dd.set_variant("shadow")
        assert dd.trigger_widget()._variant == "solid"
        dd.set_variant("bordered")
        assert dd.trigger_widget()._variant == "bordered"

    def test_set_color(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.set_color("primary")
        assert dd._color == "primary"
        assert dd._listbox._color == "primary"

    def test_set_size_propagates(self, qtbot):
        dd = Dropdown(size="sm")
        qtbot.addWidget(dd)
        dd.set_size("lg")
        assert dd._size == "lg"
        assert dd._listbox._size == "lg"
        assert dd._menu_min_width() == DROPDOWN_SIZES["lg"]["menu_min_width"]

    def test_set_radius_and_placement(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.set_radius("lg")
        assert dd._radius == "lg"
        # 圆角同时下发到菜单项，避免菜单方角戳出浮层圆角
        assert dd._listbox._radius == "lg"
        dd.set_placement("top-end")
        assert dd._placement == "top-end"
        assert dd._popover._placement == "top-end"

    def test_set_hide_selected_icon(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.set_hide_selected_icon(True)
        assert dd._listbox._hide_selected_icon is True

    def test_set_empty_content(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.set_empty_content("没有可用操作")
        assert dd._listbox._empty_content_text == "没有可用操作"

    def test_set_disable_animation(self, qtbot):
        dd = Dropdown()
        qtbot.addWidget(dd)
        dd.set_disable_animation(True)
        assert dd._disable_animation is True
        assert dd._listbox._disable_animation is True

    def test_per_item_color_reapplied_after_set_color(self, qtbot):
        dd = Dropdown(items=[{"key": "del", "label": "Delete", "color": "danger"}])
        qtbot.addWidget(dd)
        dd.set_color("primary")
        # 单项配色不会被 listbox 统一下发吃掉
        assert dd.item_by_key("del")._color == "danger"


# ============================================================
# 主题
# ============================================================
class TestDropdownTheme:
    def test_theme_explicit(self, qtbot):
        dd = Dropdown(theme="dark")
        qtbot.addWidget(dd)
        assert dd._theme == "dark"
        assert dd._theme_mode == "dark"

    def test_set_theme_dynamic(self, qtbot):
        dd = Dropdown(theme="light")
        qtbot.addWidget(dd)
        dd.set_theme("dark")
        assert dd._theme == "dark"

    def test_set_theme_invalid_ignored(self, qtbot):
        dd = Dropdown(theme="light")
        qtbot.addWidget(dd)
        dd.set_theme("blue")
        assert dd._theme == "light"

    def test_set_theme_auto_registers(self, qtbot):
        dd = Dropdown(theme="light")
        qtbot.addWidget(dd)
        dd.set_theme("auto")
        assert dd._theme_mode == "auto"


# ============================================================
# 别名
# ============================================================
class TestDropdownAliases:
    def test_alias_types(self):
        assert DropdownItem is ListboxItem
        assert DropdownSection is ListboxSection
