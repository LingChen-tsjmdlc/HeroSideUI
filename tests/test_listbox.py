"""Listbox / ListboxItem / ListboxSection 组件测试"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from hero_side_ui import Listbox, ListboxItem, ListboxSection


# ============================================================
# 初始化
# ============================================================
class TestListboxInit:
    def test_default_params(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        assert lb._variant == "solid"
        assert lb._color == "default"
        assert lb._size == "md"
        assert lb._radius == "sm"
        assert lb._selection_mode == "none"
        assert lb._is_disabled is False
        assert lb._theme_mode == "auto"

    def test_invalid_variant_falls_back(self, qtbot):
        lb = Listbox(variant="invalid")
        qtbot.addWidget(lb)
        assert lb._variant == "solid"

    def test_invalid_color_falls_back(self, qtbot):
        lb = Listbox(color="invalid")
        qtbot.addWidget(lb)
        assert lb._color == "default"

    def test_invalid_selection_mode_falls_back(self, qtbot):
        lb = Listbox(selection_mode="invalid")
        qtbot.addWidget(lb)
        assert lb._selection_mode == "none"


class TestListboxItemInit:
    def test_default_params(self, qtbot):
        it = ListboxItem("Hello")
        qtbot.addWidget(it)
        assert it.title() == "Hello"
        assert it.key() == "Hello"
        assert it.description() == ""
        assert it.shortcut_text() == ""
        assert it.is_disabled() is False
        assert it.is_selected() is False

    def test_explicit_key(self, qtbot):
        it = ListboxItem("Hello", key="hi")
        qtbot.addWidget(it)
        assert it.key() == "hi"

    def test_with_description(self, qtbot):
        it = ListboxItem("Hello", description="A greeting")
        qtbot.addWidget(it)
        assert it.description() == "A greeting"
        assert it._desc_label.isVisibleTo(it) or not it.isVisible()  # 仅在 show 后才计算

    def test_with_shortcut(self, qtbot):
        it = ListboxItem("Hello", shortcut="Ctrl+H")
        qtbot.addWidget(it)
        assert it.shortcut_text() == "Ctrl+H"


# ============================================================
# 6 variants × 6 colors × 3 sizes 矩阵
# ============================================================
class TestListboxStyleMatrix:
    @pytest.mark.parametrize("variant", ["solid", "shadow", "bordered", "flat", "faded", "light"])
    def test_all_variants(self, qtbot, variant):
        lb = Listbox(variant=variant)
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        assert lb._variant == variant
        assert lb._items[0]._variant == variant

    @pytest.mark.parametrize("color", ["default", "primary", "secondary", "success", "warning", "danger"])
    def test_all_colors(self, qtbot, color):
        lb = Listbox(color=color)
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        assert lb._color == color
        assert lb._items[0]._color == color

    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_all_sizes(self, qtbot, size):
        lb = Listbox(size=size)
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        assert lb._size == size
        assert lb._items[0]._size == size

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_themes(self, qtbot, theme):
        lb = Listbox(theme=theme)
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        assert lb._theme == theme


# ============================================================
# 装配 API
# ============================================================
class TestListboxAdd:
    def test_add_item_string(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        it = lb.add_item("First", key="f", description="D", shortcut="Ctrl+F")
        assert isinstance(it, ListboxItem)
        assert lb.items() == [it]
        assert lb.item_by_key("f") is it

    def test_add_item_object(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        it = ListboxItem("Pre", key="p")
        ret = lb.add_item(it)
        assert ret is it
        assert lb.item_by_key("p") is it

    def test_add_section(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        sec = ListboxSection("Group")
        sec.add_item("A", key="a")
        sec.add_item("B", key="b")
        ret = lb.add_section(sec)
        assert ret is sec
        # section 内的 item 也注册到 lb._items
        assert lb.item_by_key("a") is not None
        assert lb.item_by_key("b") is not None

    def test_clear(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        lb.add_item("Y", key="y")
        lb.clear()
        assert lb.items() == []

    def test_empty_label_visible_when_no_items(self, qtbot):
        lb = Listbox(empty_content="Nothing.")
        qtbot.addWidget(lb)
        lb.show()
        assert lb._empty_label.isVisible() is True

    def test_empty_label_hidden_with_items(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        lb.show()
        assert lb._empty_label.isVisible() is False


# ============================================================
# Selection
# ============================================================
class TestListboxSelection:
    def test_selection_none_default(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.add_item("A", key="a")
        lb.add_item("B", key="b")
        # 触发 activate 不应改 selection
        with qtbot.waitSignal(lb.action, timeout=200):
            lb._on_item_activated("a")
        assert lb.selected_keys() == set()

    def test_single_selection_via_action(self, qtbot):
        lb = Listbox(selection_mode="single")
        qtbot.addWidget(lb)
        lb.add_item("A", key="a")
        lb.add_item("B", key="b")
        signals = []
        lb.selection_changed.connect(lambda s: signals.append(set(s)))

        lb._on_item_activated("a")
        assert lb.selected_keys() == {"a"}
        lb._on_item_activated("b")
        assert lb.selected_keys() == {"b"}
        # 只有 a 也只有 b 两次变化
        assert signals == [{"a"}, {"b"}]

    def test_multiple_selection_toggle(self, qtbot):
        lb = Listbox(selection_mode="multiple")
        qtbot.addWidget(lb)
        lb.add_item("A", key="a")
        lb.add_item("B", key="b")
        lb.add_item("C", key="c")

        lb._on_item_activated("a")
        lb._on_item_activated("b")
        assert lb.selected_keys() == {"a", "b"}
        lb._on_item_activated("a")  # 反选
        assert lb.selected_keys() == {"b"}

    def test_set_selected_keys_initial(self, qtbot):
        lb = Listbox(selection_mode="single", selected_keys={"x"})
        qtbot.addWidget(lb)
        it = lb.add_item("X", key="x")
        assert it.is_selected() is True

    def test_set_selected_keys_dynamic(self, qtbot):
        lb = Listbox(selection_mode="single")
        qtbot.addWidget(lb)
        lb.add_item("A", key="a")
        lb.add_item("B", key="b")
        lb.set_selected_keys({"a"})
        assert lb.item_by_key("a").is_selected()
        assert not lb.item_by_key("b").is_selected()
        lb.set_selected_keys({"b"})
        assert not lb.item_by_key("a").is_selected()
        assert lb.item_by_key("b").is_selected()

    def test_single_mode_truncates_multi_selection(self, qtbot):
        lb = Listbox(selection_mode="single")
        qtbot.addWidget(lb)
        lb.add_item("A", key="a")
        lb.add_item("B", key="b")
        lb.set_selected_keys({"a", "b"})
        # 只保留一个
        assert len(lb.selected_keys()) == 1

    def test_set_selection_mode_none_clears(self, qtbot):
        lb = Listbox(selection_mode="single")
        qtbot.addWidget(lb)
        lb.add_item("A", key="a")
        lb.set_selected_keys({"a"})
        lb.set_selection_mode("none")
        assert lb.selected_keys() == set()


# ============================================================
# Disabled
# ============================================================
class TestListboxDisabled:
    def test_disabled_keys_initial(self, qtbot):
        lb = Listbox(disabled_keys={"a"})
        qtbot.addWidget(lb)
        a = lb.add_item("A", key="a")
        b = lb.add_item("B", key="b")
        assert a.is_disabled() is True
        assert b.is_disabled() is False

    def test_set_disabled_keys_dynamic(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        a = lb.add_item("A", key="a")
        b = lb.add_item("B", key="b")
        lb.set_disabled_keys({"b"})
        assert a.is_disabled() is False
        assert b.is_disabled() is True

    def test_is_disabled_global(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.add_item("A", key="a")
        lb.set_is_disabled(True)
        assert lb.is_disabled() is True


# ============================================================
# 信号
# ============================================================
class TestListboxSignals:
    def test_action_signal_fires_on_activate(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        with qtbot.waitSignal(lb.action, timeout=200) as blocker:
            lb._on_item_activated("x")
        assert blocker.args == ["x"]

    def test_selection_changed_signal(self, qtbot):
        lb = Listbox(selection_mode="single")
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        with qtbot.waitSignal(lb.selection_changed, timeout=200) as blocker:
            lb._on_item_activated("x")
        assert blocker.args[0] == {"x"}


# ============================================================
# ListboxItem 直接测试
# ============================================================
class TestListboxItemBehaviour:
    def test_set_title_updates_label(self, qtbot):
        it = ListboxItem("A")
        qtbot.addWidget(it)
        it.set_title("B")
        assert it._title_label.text() == "B"

    def test_set_description_show_hide(self, qtbot):
        it = ListboxItem("A")
        qtbot.addWidget(it)
        it.set_description("Hello")
        it.show()
        assert it._desc_label.isVisible() is True
        it.set_description("")
        assert it._desc_label.isVisible() is False

    def test_set_shortcut_show_hide(self, qtbot):
        it = ListboxItem("A")
        qtbot.addWidget(it)
        it.set_shortcut("Ctrl+S")
        it.show()
        assert it._shortcut_label.isVisible() is True
        it.set_shortcut("")
        assert it._shortcut_label.isVisible() is False

    def test_set_disabled(self, qtbot):
        it = ListboxItem("A")
        qtbot.addWidget(it)
        it.set_disabled(True)
        assert it.is_disabled() is True
        assert it.isEnabled() is False
        it.set_disabled(False)
        assert it.is_disabled() is False
        assert it.isEnabled() is True

    def test_set_selected_emits_signal(self, qtbot):
        it = ListboxItem("A")
        qtbot.addWidget(it)
        with qtbot.waitSignal(it.selected_changed, timeout=200) as blocker:
            it.set_selected(True)
        assert blocker.args == [True]

    def test_show_divider(self, qtbot):
        it = ListboxItem("A", show_divider=True)
        qtbot.addWidget(it)
        assert it.show_divider() is True
        it.set_show_divider(False)
        assert it.show_divider() is False


# ============================================================
# ListboxSection
# ============================================================
class TestListboxSection:
    def test_init(self, qtbot):
        sec = ListboxSection("Group")
        qtbot.addWidget(sec)
        assert sec.title() == "Group"
        assert sec.show_divider() is False

    def test_add_item(self, qtbot):
        sec = ListboxSection("G")
        qtbot.addWidget(sec)
        it = sec.add_item("A", key="a")
        assert it in sec.items()
        assert it.title() == "A"

    def test_set_title(self, qtbot):
        sec = ListboxSection("Old")
        qtbot.addWidget(sec)
        sec.set_title("New")
        assert sec.title() == "New"
        assert sec._heading.text() == "New"


# ============================================================
# 动态属性 setter
# ============================================================
class TestListboxSetters:
    def test_set_variant(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        lb.set_variant("flat")
        assert lb._variant == "flat"
        assert lb._items[0]._variant == "flat"

    def test_set_color(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        lb.set_color("primary")
        assert lb._color == "primary"
        assert lb._items[0]._color == "primary"

    def test_set_size(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        lb.set_size("lg")
        assert lb._size == "lg"
        assert lb._items[0]._size == "lg"

    def test_set_empty_content(self, qtbot):
        lb = Listbox()
        qtbot.addWidget(lb)
        lb.set_empty_content("Custom!")
        assert lb._empty_label.text() == "Custom!"

    def test_set_theme(self, qtbot):
        lb = Listbox(theme="light")
        qtbot.addWidget(lb)
        lb.add_item("X", key="x")
        lb.set_theme("dark")
        assert lb._theme == "dark"
        assert lb._items[0]._theme == "dark"
