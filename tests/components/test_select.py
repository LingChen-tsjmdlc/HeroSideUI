"""Select 组件测试"""

import pytest
from PySide6.QtCore import Qt

from hero_side_ui import Select
from hero_side_ui.themes import SELECT_SIZES


# ============================================================
# 初始化
# ============================================================
class TestSelectInit:
    def test_default_params(self, qtbot):
        sel = Select()
        qtbot.addWidget(sel)
        assert sel._variant == "flat"
        assert sel._color == "default"
        assert sel._size == "md"
        assert sel._selection_mode == "single"
        assert sel._is_clearable is False
        assert sel._disallow_empty_selection is False
        assert sel._disable_selector_icon_rotation is False
        assert sel._theme_mode == "auto"
        assert sel.selected_keys() == set()
        assert sel.selected_key() is None
        assert sel.is_open() is False
        # Select 与 Autocomplete 一样：下拉方向必须保持向下
        assert sel._popover._allow_flip is False
        # trigger 内 line_edit 永远 readOnly
        assert sel._input.line_edit.isReadOnly() is True

    def test_with_items(self, qtbot):
        sel = Select(items=[("a", "Apple"), ("b", "Banana")])
        qtbot.addWidget(sel)
        assert len(sel.items()) == 2
        assert sel.item_by_key("a").title() == "Apple"

    def test_default_selected_keys_single(self, qtbot):
        sel = Select(
            items=[("cat", "Cat"), ("dog", "Dog")], default_selected_keys={"cat"}
        )
        qtbot.addWidget(sel)
        assert sel.selected_key() == "cat"
        assert sel._input.text() == "Cat"

    def test_default_selected_keys_multiple(self, qtbot):
        sel = Select(
            items=[("a", "Apple"), ("b", "Banana"), ("c", "Cherry")],
            selection_mode="multiple",
            default_selected_keys={"a", "b"},
        )
        qtbot.addWidget(sel)
        assert sel.selected_keys() == {"a", "b"}
        # 文本按 items 顺序拼接
        assert "Apple" in sel._input.text()
        assert "Banana" in sel._input.text()

    def test_single_mode_collapses_multiple_initial(self, qtbot):
        sel = Select(
            items=[("a", "Apple"), ("b", "Banana")],
            selection_mode="single",
            default_selected_keys={"a", "b"},
        )
        qtbot.addWidget(sel)
        assert len(sel.selected_keys()) == 1

    def test_invalid_variant_fallback(self, qtbot):
        sel = Select(variant="invalid")
        qtbot.addWidget(sel)
        assert sel._variant == "flat"

    def test_invalid_size_fallback(self, qtbot):
        sel = Select(size="huge")
        qtbot.addWidget(sel)
        assert sel._size == "md"

    def test_invalid_selection_mode_fallback(self, qtbot):
        sel = Select(selection_mode="weird")
        qtbot.addWidget(sel)
        assert sel._selection_mode == "single"


# ============================================================
# 选中行为
# ============================================================
class TestSelectSelection:
    def _make(self, qtbot, **kw):
        sel = Select(items=[("a", "Apple"), ("b", "Banana"), ("c", "Cherry")], **kw)
        qtbot.addWidget(sel)
        return sel

    def test_single_select_via_listbox_action(self, qtbot):
        sel = self._make(qtbot)
        signals = []
        sel.selection_changed.connect(lambda v: signals.append(v))
        # 模拟 listbox 内部触发选中：先在 listbox 里改 selected_keys，再发 action
        sel._listbox.set_selected_keys({"b"})
        sel._on_listbox_action("b")
        assert sel.selected_key() == "b"
        assert sel._input.text() == "Banana"
        assert signals == ["b"]

    def test_multiple_select_keeps_all(self, qtbot):
        sel = self._make(qtbot, selection_mode="multiple")
        # 模拟两次选中：直接走 listbox API
        sel._listbox.set_selected_keys({"a"})
        sel._on_listbox_action("a")
        sel._listbox.set_selected_keys({"a", "b"})
        sel._on_listbox_action("b")
        assert sel.selected_keys() == {"a", "b"}

    def test_set_selected_key_syncs(self, qtbot):
        sel = self._make(qtbot)
        sel.set_selected_key("c")
        assert sel.selected_key() == "c"
        assert sel._input.text() == "Cherry"
        assert sel._listbox.selected_keys() == {"c"}

    def test_set_selected_keys_multiple(self, qtbot):
        sel = self._make(qtbot, selection_mode="multiple")
        sel.set_selected_keys({"a", "b"})
        assert sel.selected_keys() == {"a", "b"}

    def test_set_selected_keys_collapse_in_single(self, qtbot):
        sel = self._make(qtbot, selection_mode="single")
        sel.set_selected_keys({"a", "b"})
        assert len(sel.selected_keys()) == 1

    def test_disallow_empty_selection_blocks_unselect(self, qtbot):
        sel = self._make(
            qtbot,
            selection_mode="multiple",
            disallow_empty_selection=True,
            default_selected_keys={"a"},
        )
        # 模拟用户取消最后一个选中：listbox 状态变空，应该被还原
        sel._listbox.set_selected_keys(set())
        sel._on_listbox_action("a")
        assert sel.selected_keys() == {"a"}


# ============================================================
# Clear
# ============================================================
class TestSelectClear:
    def _make(self, qtbot):
        sel = Select(
            items=[("a", "Apple"), ("b", "Banana")],
            is_clearable=True,
            default_selected_keys={"a"},
        )
        qtbot.addWidget(sel)
        return sel

    def test_clear_clears_keys_and_text(self, qtbot):
        sel = self._make(qtbot)
        sel._on_clear_clicked()
        assert sel.selected_keys() == set()
        assert sel._input.text() == ""

    def test_clear_signal(self, qtbot):
        sel = self._make(qtbot)
        with qtbot.waitSignal(sel.cleared, timeout=200):
            sel._on_clear_clicked()

    def test_clear_btn_visibility_requires_hover_or_focus(self, qtbot):
        sel = self._make(qtbot)
        sel._is_hovered = False
        sel._input.line_edit.clearFocus()
        sel._is_open = False
        sel._refresh_clear_visibility()
        assert sel._end.clear_btn.isHidden()

        sel._is_hovered = True
        sel._refresh_clear_visibility()
        assert not sel._end.clear_btn.isHidden()

    def test_is_clearable_false_hides_btn(self, qtbot):
        sel = self._make(qtbot)
        sel._is_hovered = True
        sel._refresh_clear_visibility()
        assert not sel._end.clear_btn.isHidden()
        sel.set_is_clearable(False)
        assert sel._end.clear_btn.isHidden()


# ============================================================
# 信号
# ============================================================
class TestSelectSignals:
    def test_selection_changed_single(self, qtbot):
        sel = Select(items=[("a", "Apple"), ("b", "Banana")])
        qtbot.addWidget(sel)
        with qtbot.waitSignal(sel.selection_changed, timeout=200) as blocker:
            sel._listbox.set_selected_keys({"b"})
            sel._on_listbox_action("b")
        assert blocker.args == ["b"]

    def test_selection_changed_multiple_payload_is_set(self, qtbot):
        sel = Select(items=[("a", "Apple"), ("b", "Banana")], selection_mode="multiple")
        qtbot.addWidget(sel)
        with qtbot.waitSignal(sel.selection_changed, timeout=200) as blocker:
            sel._listbox.set_selected_keys({"a"})
            sel._on_listbox_action("a")
        assert blocker.args == [{"a"}]


# ============================================================
# 透传 setter
# ============================================================
class TestSelectSetters:
    def test_set_color(self, qtbot):
        sel = Select()
        qtbot.addWidget(sel)
        sel.set_color("primary")
        assert sel._color == "primary"
        assert sel._input._color == "primary"

    def test_set_size_updates_subwidgets(self, qtbot):
        sel = Select()
        qtbot.addWidget(sel)
        sel.set_size("lg")
        assert sel._size == "lg"
        assert sel._input._size == "lg"
        assert sel._listbox._size == "lg"

    def test_set_variant(self, qtbot):
        sel = Select()
        qtbot.addWidget(sel)
        sel.set_variant("bordered")
        assert sel._variant == "bordered"

    def test_set_selection_mode_collapse(self, qtbot):
        sel = Select(
            items=[("a", "Apple"), ("b", "Banana")],
            selection_mode="multiple",
            default_selected_keys={"a", "b"},
        )
        qtbot.addWidget(sel)
        sel.set_selection_mode("single")
        assert sel._selection_mode == "single"
        assert len(sel.selected_keys()) == 1

    def test_set_disabled_propagates(self, qtbot):
        sel = Select()
        qtbot.addWidget(sel)
        sel.set_is_disabled(True)
        assert sel._is_disabled is True
        assert sel._input._is_disabled is True

    def test_set_is_readonly_marks_all_disabled(self, qtbot):
        sel = Select(items=[("a", "Apple"), ("b", "Banana")])
        qtbot.addWidget(sel)
        sel.set_is_readonly(True)
        # readonly 时所有 item 都进入 disabled_keys（对齐 HeroUI 语义）
        assert sel._listbox._disabled_keys == {"a", "b"}

    def test_set_disabled_keys(self, qtbot):
        sel = Select(items=[("a", "Apple"), ("b", "Banana")])
        qtbot.addWidget(sel)
        sel.set_disabled_keys({"b"})
        assert sel._listbox._disabled_keys == {"b"}


# ============================================================
# items 重置
# ============================================================
class TestSelectItemsReset:
    def test_set_items_clears_old(self, qtbot):
        sel = Select(items=[("a", "Apple")])
        qtbot.addWidget(sel)
        assert len(sel.items()) == 1
        sel.set_items([("b", "Banana"), ("c", "Cherry")])
        assert len(sel.items()) == 2
        assert sel.item_by_key("a") is None


# ============================================================
# 主题
# ============================================================
class TestSelectTheme:
    def test_theme_light(self, qtbot):
        sel = Select(theme="light")
        qtbot.addWidget(sel)
        assert sel._theme == "light"

    def test_theme_dark(self, qtbot):
        sel = Select(theme="dark")
        qtbot.addWidget(sel)
        assert sel._theme == "dark"

    def test_set_theme_dynamic(self, qtbot):
        sel = Select(theme="light")
        qtbot.addWidget(sel)
        sel.set_theme("dark")
        assert sel._theme == "dark"


# ============================================================
# Popover
# ============================================================
class TestSelectPopover:
    def test_open_close(self, qtbot):
        sel = Select(items=[("a", "Apple")], disable_animation=True)
        qtbot.addWidget(sel)
        qtbot.addWidget(sel._popover)
        sel.show()
        qtbot.waitExposed(sel)
        sel.open()
        qtbot.waitUntil(lambda: sel._popover.is_open() is True, timeout=2000)
        sel.close()
        qtbot.waitUntil(lambda: sel._popover.is_open() is False, timeout=2000)

    def test_toggle(self, qtbot):
        sel = Select(items=[("a", "Apple")], disable_animation=True)
        qtbot.addWidget(sel)
        qtbot.addWidget(sel._popover)

        call_log = []
        orig_open = sel.open
        orig_close = sel.close

        def spy_open():
            call_log.append("open")
            orig_open()

        def spy_close():
            call_log.append("close")
            orig_close()

        sel.open = spy_open
        sel.close = spy_close

        assert sel._is_open is False
        sel.toggle()
        assert "open" in call_log

        call_log.clear()
        sel._is_open = True
        sel.toggle()
        assert "close" in call_log

    def test_long_list_uses_md_popover_max_height(self, qtbot):
        sel = Select(items=[(str(i), f"Item {i}") for i in range(30)])
        qtbot.addWidget(sel)
        expected = SELECT_SIZES["md"]["popover_max_height"]
        assert sel._scroll.minimumHeight() == expected
        assert sel._scroll.maximumHeight() == expected

    def test_set_size_updates_popover_fixed_height(self, qtbot):
        sel = Select(items=[(str(i), f"Item {i}") for i in range(30)])
        qtbot.addWidget(sel)
        sel.set_size("lg")
        expected = SELECT_SIZES["lg"]["popover_max_height"]
        assert sel._scroll.minimumHeight() == expected
        assert sel._scroll.maximumHeight() == expected


# ============================================================
# Trigger 文本同步
# ============================================================
class TestSelectTriggerText:
    def test_single_text_is_label(self, qtbot):
        sel = Select(items=[("a", "Apple"), ("b", "Banana")])
        qtbot.addWidget(sel)
        sel.set_selected_key("a")
        assert sel._input.text() == "Apple"

    def test_multiple_text_joined_by_comma(self, qtbot):
        sel = Select(
            items=[("a", "Apple"), ("b", "Banana"), ("c", "Cherry")],
            selection_mode="multiple",
        )
        qtbot.addWidget(sel)
        sel.set_selected_keys({"a", "b"})
        assert "Apple" in sel._input.text()
        assert "Banana" in sel._input.text()

    def test_multiple_text_overflow_uses_plus_n(self, qtbot):
        items = [(f"k{i}", f"Label{i}") for i in range(10)]
        sel = Select(items=items, selection_mode="multiple", size="md")
        qtbot.addWidget(sel)
        # md 的 chip_max=3，全选会出 +N
        sel.set_selected_keys({k for k, _ in items})
        assert "+" in sel._input.text()
