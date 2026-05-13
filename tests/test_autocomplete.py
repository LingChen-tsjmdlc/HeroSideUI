"""Autocomplete 组件测试"""

import pytest
from PySide6.QtCore import Qt

from hero_side_ui import Autocomplete


# ============================================================
# 初始化
# ============================================================
class TestAutocompleteInit:
    def test_default_params(self, qtbot):
        ac = Autocomplete()
        qtbot.addWidget(ac)
        assert ac._variant == "flat"
        assert ac._color == "default"
        assert ac._size == "md"
        assert ac._menu_trigger == "focus"
        assert ac._is_clearable is True
        assert ac._allows_custom_value is False
        assert ac._disable_selector_icon_rotation is False
        assert ac._theme_mode == "auto"
        assert ac.selected_key() is None
        assert ac.input_value() == ""
        assert ac.is_open() is False

    def test_with_items(self, qtbot):
        ac = Autocomplete(items=[
            {"key": "a", "label": "Apple"},
            {"key": "b", "label": "Banana"},
        ])
        qtbot.addWidget(ac)
        assert len(ac.items()) == 2
        assert ac.item_by_key("a").title() == "Apple"

    def test_tuple_items(self, qtbot):
        ac = Autocomplete(items=[("a", "Apple"), ("b", "Banana")])
        qtbot.addWidget(ac)
        assert len(ac.items()) == 2
        assert ac.item_by_key("a").title() == "Apple"

    def test_default_selected_key(self, qtbot):
        ac = Autocomplete(
            items=[("cat", "Cat"), ("dog", "Dog")],
            default_selected_key="cat",
        )
        qtbot.addWidget(ac)
        assert ac.selected_key() == "cat"
        assert ac.input_value() == "Cat"

    def test_default_input_value(self, qtbot):
        ac = Autocomplete(default_input_value="hello")
        qtbot.addWidget(ac)
        assert ac.input_value() == "hello"

    def test_invalid_variant_fallback(self, qtbot):
        ac = Autocomplete(variant="invalid")
        qtbot.addWidget(ac)
        assert ac._variant == "flat"

    def test_invalid_size_fallback(self, qtbot):
        ac = Autocomplete(size="huge")
        qtbot.addWidget(ac)
        assert ac._size == "md"

    def test_invalid_menu_trigger_fallback(self, qtbot):
        ac = Autocomplete(menu_trigger="weird")
        qtbot.addWidget(ac)
        assert ac._menu_trigger == "focus"


# ============================================================
# 过滤
# ============================================================
class TestAutocompleteFilter:
    def _make(self, qtbot):
        ac = Autocomplete(items=[
            ("a", "Apple"), ("b", "Banana"), ("c", "Cherry"), ("d", "Date"),
        ])
        qtbot.addWidget(ac)
        return ac

    def test_contains_default(self, qtbot):
        ac = self._make(qtbot)
        ac.set_input_value("an")
        # contains 'an' (case-insensitive) → Banana / Date 不含；Apple 不含；Banana 含；
        # 让我检查每个真实结果
        visible = [it.title() for it in ac.items() if not it.isHidden()]
        # 'Banana' 包含 'an'
        assert "Banana" in visible
        # 'Apple' / 'Cherry' / 'Date' 不包含 'an'
        assert "Apple" not in visible

    def test_case_insensitive(self, qtbot):
        ac = self._make(qtbot)
        ac.set_input_value("APP")
        visible = [it.title() for it in ac.items() if not it.isHidden()]
        assert "Apple" in visible

    def test_empty_query_shows_all(self, qtbot):
        ac = self._make(qtbot)
        ac.set_input_value("an")
        ac.set_input_value("")
        visible = [it.title() for it in ac.items() if not it.isHidden()]
        assert len(visible) == 4

    def test_custom_filter(self, qtbot):
        # 只匹配以 query 开头的项（startsWith）
        def starts_with(label, q):
            return label.lower().startswith(q.lower()) if q else True
        ac = Autocomplete(
            items=[("a", "Apple"), ("b", "Banana"), ("ap", "Apricot")],
            default_filter=starts_with,
        )
        qtbot.addWidget(ac)
        ac.set_input_value("ap")
        visible = [it.title() for it in ac.items() if not it.isHidden()]
        assert visible == ["Apple", "Apricot"]

    def test_set_default_filter_dynamic(self, qtbot):
        ac = self._make(qtbot)
        ac.set_input_value("a")
        # 默认 contains 下 'a' 匹配 Apple/Banana/Date
        visible1 = [it.title() for it in ac.items() if not it.isHidden()]
        assert "Date" in visible1
        # 切到 startsWith
        ac.set_default_filter(
            lambda label, q: label.lower().startswith(q.lower()) if q else True
        )
        visible2 = [it.title() for it in ac.items() if not it.isHidden()]
        assert visible2 == ["Apple"]


# ============================================================
# 选中流程
# ============================================================
class TestAutocompleteSelection:
    def _make(self, qtbot):
        ac = Autocomplete(items=[
            ("cat", "Cat"), ("dog", "Dog"), ("bird", "Bird"),
        ])
        qtbot.addWidget(ac)
        return ac

    def test_listbox_action_selects(self, qtbot):
        ac = self._make(qtbot)
        signals = []
        ac.selection_changed.connect(lambda k: signals.append(k))
        ac._on_listbox_action("dog")
        assert ac.selected_key() == "dog"
        assert ac.input_value() == "Dog"
        assert signals == ["dog"]

    def test_set_selected_key_syncs_input(self, qtbot):
        ac = self._make(qtbot)
        ac.set_selected_key("cat")
        assert ac.selected_key() == "cat"
        assert ac.input_value() == "Cat"

    def test_set_selected_key_none_clears_listbox(self, qtbot):
        ac = self._make(qtbot)
        ac.set_selected_key("cat")
        ac.set_selected_key(None)
        assert ac.selected_key() is None
        assert ac.item_by_key("cat").is_selected() is False

    def test_typing_clears_selection(self, qtbot):
        ac = self._make(qtbot)
        ac.set_selected_key("cat")
        # 模拟用户改 input.text
        ac._input.set_text("Cattle")  # 不再匹配 "Cat"
        assert ac.selected_key() is None


# ============================================================
# Clear 行为
# ============================================================
class TestAutocompleteClear:
    def _make(self, qtbot):
        ac = Autocomplete(items=[("a", "Apple"), ("b", "Banana")])
        qtbot.addWidget(ac)
        return ac

    def test_clear_clears_both(self, qtbot):
        ac = self._make(qtbot)
        ac.set_selected_key("a")
        ac._on_clear_clicked()
        assert ac.selected_key() is None
        assert ac.input_value() == ""

    def test_clear_signal(self, qtbot):
        ac = self._make(qtbot)
        ac.set_selected_key("a")
        with qtbot.waitSignal(ac.cleared, timeout=200):
            ac._on_clear_clicked()

    def test_clear_btn_visible_only_with_value(self, qtbot):
        ac = self._make(qtbot)
        # 触发 hover 模拟用户鼠标在组件上（HeroUI 行为：hover 才显示 clear）
        ac._is_hovered = True
        ac._refresh_clear_visibility()
        assert ac._end.clear_btn.isHidden()  # 初始无值，clear 隐藏
        ac.set_selected_key("a")
        assert not ac._end.clear_btn.isHidden()  # 有值 + hover → 显示
        ac._on_clear_clicked()
        assert ac._end.clear_btn.isHidden()  # 清空后又隐藏

    def test_is_clearable_false_hides_btn(self, qtbot):
        ac = self._make(qtbot)
        ac._is_hovered = True
        ac.set_selected_key("a")
        ac._refresh_clear_visibility()
        assert not ac._end.clear_btn.isHidden()
        ac.set_is_clearable(False)
        assert ac._end.clear_btn.isHidden()

    def test_clear_btn_hidden_without_hover_or_focus(self, qtbot):
        """对齐 HeroUI: 有值但既未 hover 也未 focus 时,clear 不应显示。"""
        ac = self._make(qtbot)
        ac.set_selected_key("a")  # 有值
        ac._is_hovered = False
        # 强制确保未聚焦
        ac._input.line_edit.clearFocus()
        ac._is_open = False
        ac._refresh_clear_visibility()
        assert ac._end.clear_btn.isHidden(), "未 hover/focus 时 clear 应该隐藏"


# ============================================================
# 信号
# ============================================================
class TestAutocompleteSignals:
    def test_input_changed_on_user_typing(self, qtbot):
        ac = Autocomplete(items=[("a", "Apple")])
        qtbot.addWidget(ac)
        with qtbot.waitSignal(ac.input_changed, timeout=200) as blocker:
            ac._input.set_text("Hello")
        assert blocker.args == ["Hello"]

    def test_selection_changed_emitted_on_action(self, qtbot):
        ac = Autocomplete(items=[("a", "Apple"), ("b", "Banana")])
        qtbot.addWidget(ac)
        with qtbot.waitSignal(ac.selection_changed, timeout=200) as blocker:
            ac._on_listbox_action("b")
        assert blocker.args == ["b"]


# ============================================================
# 透传 setter
# ============================================================
class TestAutocompleteSetters:
    def test_set_color(self, qtbot):
        ac = Autocomplete()
        qtbot.addWidget(ac)
        ac.set_color("primary")
        assert ac._color == "primary"
        assert ac._input._color == "primary"

    def test_set_size_updates_subwidgets(self, qtbot):
        ac = Autocomplete()
        qtbot.addWidget(ac)
        ac.set_size("lg")
        assert ac._size == "lg"
        assert ac._input._size == "lg"
        assert ac._listbox._size == "lg"

    def test_set_variant(self, qtbot):
        ac = Autocomplete()
        qtbot.addWidget(ac)
        ac.set_variant("bordered")
        assert ac._variant == "bordered"

    def test_set_label_placeholder_description(self, qtbot):
        ac = Autocomplete()
        qtbot.addWidget(ac)
        ac.set_label("Name")
        ac.set_placeholder("Type...")
        ac.set_description("Helpful text")
        assert ac._input._label_text == "Name"
        assert ac._input._placeholder == "Type..."
        assert ac._input._description == "Helpful text"

    def test_set_disabled_propagates(self, qtbot):
        ac = Autocomplete()
        qtbot.addWidget(ac)
        ac.set_is_disabled(True)
        assert ac._is_disabled is True
        assert ac._input._is_disabled is True


# ============================================================
# items 重置
# ============================================================
class TestAutocompleteItemsReset:
    def test_set_items_clears_old(self, qtbot):
        ac = Autocomplete(items=[("a", "Apple")])
        qtbot.addWidget(ac)
        assert len(ac.items()) == 1
        ac.set_items([("b", "Banana"), ("c", "Cherry")])
        assert len(ac.items()) == 2
        assert ac.item_by_key("a") is None
        assert ac.item_by_key("b") is not None


# ============================================================
# 主题
# ============================================================
class TestAutocompleteTheme:
    def test_theme_light(self, qtbot):
        ac = Autocomplete(theme="light")
        qtbot.addWidget(ac)
        assert ac._theme == "light"

    def test_theme_dark(self, qtbot):
        ac = Autocomplete(theme="dark")
        qtbot.addWidget(ac)
        assert ac._theme == "dark"

    def test_set_theme_dynamic(self, qtbot):
        ac = Autocomplete(theme="light")
        qtbot.addWidget(ac)
        ac.set_theme("dark")
        assert ac._theme == "dark"


# ============================================================
# 滚动 popover 关联
# ============================================================
class TestAutocompletePopover:
    def test_open_close(self, qtbot):
        ac = Autocomplete(items=[("a", "Apple")], disable_animation=True)
        qtbot.addWidget(ac)
        ac.show()
        qtbot.waitExposed(ac)
        ac.open()
        qtbot.waitUntil(lambda: ac._popover.is_open() is True, timeout=2000)
        ac.close()
        qtbot.waitUntil(lambda: ac._popover.is_open() is False, timeout=2000)

    def test_toggle(self, qtbot):
        ac = Autocomplete(items=[("a", "Apple")], disable_animation=True)
        qtbot.addWidget(ac)
        ac.show()
        qtbot.waitExposed(ac)
        ac.toggle()
        # CI 上 toggle → open → popover.show() 之间可能有 timing 间隙，用 waitUntil 兜底
        # 取代裸 assert（macOS CI 偶发 flaky；不是逻辑 bug）
        qtbot.waitUntil(lambda: ac._popover.is_open() is True, timeout=2000)
        ac.toggle()
        qtbot.waitUntil(lambda: ac._popover.is_open() is False, timeout=2000)
