"""Input 组件测试"""

import pytest
from PySide6.QtCore import Qt

from hero_side_ui import Input


class TestInputInit:
    """构造参数测试"""

    def test_default_params(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        assert inp.text() == ""
        assert inp._variant == "flat"
        assert inp._color == "default"
        assert inp._size == "md"
        assert inp._label_placement == "inside"
        assert inp._theme == "light"
        assert not inp._is_disabled
        assert not inp._is_invalid

    def test_custom_params(self, qtbot):
        inp = Input(
            label="Email",
            value="hello",
            placeholder="type...",
            variant="bordered",
            color="primary",
            size="lg",
            radius="full",
            label_placement="outside",
            is_required=True,
            is_clearable=True,
            description="desc",
            theme="dark",
        )
        qtbot.addWidget(inp)
        assert inp.text() == "hello"
        assert inp._variant == "bordered"
        assert inp._color == "primary"
        assert inp._size == "lg"
        assert inp._radius == "full"
        assert inp._label_placement == "outside"
        assert inp._is_required
        assert inp._is_clearable
        assert inp._theme == "dark"

    def test_disabled(self, qtbot):
        inp = Input(label="x", is_disabled=True)
        qtbot.addWidget(inp)
        assert inp._is_disabled
        assert not inp.line_edit.isEnabled()

    def test_readonly(self, qtbot):
        inp = Input(label="x", is_readonly=True)
        qtbot.addWidget(inp)
        assert inp.line_edit.isReadOnly()


class TestInputVariants:
    @pytest.mark.parametrize("variant", ["flat", "faded", "bordered", "underlined"])
    def test_all_variants(self, qtbot, variant):
        inp = Input(label="L", variant=variant)
        qtbot.addWidget(inp)
        assert inp._variant == variant


class TestInputColors:
    @pytest.mark.parametrize(
        "color", ["default", "primary", "secondary", "success", "warning", "danger"]
    )
    def test_all_colors(self, qtbot, color):
        inp = Input(label="L", color=color)
        qtbot.addWidget(inp)
        assert inp._color == color


class TestInputSizes:
    @pytest.mark.parametrize("size", ["sm", "md", "lg", "small", "medium", "large"])
    def test_all_sizes(self, qtbot, size):
        inp = Input(label="L", size=size)
        qtbot.addWidget(inp)
        assert inp._size == size


class TestInputLabelPlacement:
    @pytest.mark.parametrize(
        "placement", ["inside", "outside", "outside-top", "outside-left"]
    )
    def test_all_placements(self, qtbot, placement):
        inp = Input(label="L", label_placement=placement)
        qtbot.addWidget(inp)
        assert inp._label_placement == placement


class TestInputCombinations:
    """遍历关键组合不崩"""

    def test_all_variant_color_size_combos(self, qtbot):
        for v in ["flat", "faded", "bordered", "underlined"]:
            for c in ["default", "primary", "secondary", "success", "warning", "danger"]:
                for s in ["sm", "md", "lg"]:
                    inp = Input(label=f"{v}-{c}", variant=v, color=c, size=s)
                    qtbot.addWidget(inp)
                    assert inp._variant == v and inp._color == c and inp._size == s


class TestInputDynamicAPI:
    def test_set_text_clear(self, qtbot):
        inp = Input(label="L")
        qtbot.addWidget(inp)
        inp.set_text("abc")
        assert inp.text() == "abc"
        inp.clear()
        assert inp.text() == ""

    def test_set_variant(self, qtbot):
        inp = Input(variant="flat")
        qtbot.addWidget(inp)
        inp.set_variant("bordered")
        assert inp._variant == "bordered"

    def test_set_color(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        inp.set_color("danger")
        assert inp._color == "danger"

    def test_set_size(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        inp.set_size("lg")
        assert inp._size == "lg"

    def test_set_theme(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        inp.set_theme("dark")
        assert inp._theme == "dark"

    def test_set_is_invalid(self, qtbot):
        inp = Input(error_message="err")
        qtbot.addWidget(inp)
        inp.set_is_invalid(True)
        assert inp._is_invalid
        assert not inp._helper_label.isHidden()
        assert inp._helper_label.text() == "err"

    def test_set_is_disabled(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        inp.set_is_disabled(True)
        assert inp._is_disabled
        assert not inp.line_edit.isEnabled()

    def test_set_label_placement(self, qtbot):
        inp = Input(label="x", label_placement="inside")
        qtbot.addWidget(inp)
        inp.set_label_placement("outside")
        assert inp._label_placement == "outside"

    def test_set_label(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        inp.set_label("New Label")
        assert inp._label_text == "New Label"

    def test_set_description(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        inp.set_description("desc")
        assert inp._description == "desc"
        assert not inp._helper_label.isHidden()
        assert inp._helper_label.text() == "desc"


class TestInputSignals:
    def test_text_changed_signal(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        with qtbot.waitSignal(inp.text_changed, timeout=1000) as blocker:
            inp.set_text("abc")
        assert blocker.args == ["abc"]

    def test_cleared_signal(self, qtbot):
        inp = Input(is_clearable=True)
        qtbot.addWidget(inp)
        inp.set_text("xxx")
        with qtbot.waitSignal(inp.cleared, timeout=1000):
            inp._clear_btn.click()

    def test_returned_signal(self, qtbot):
        inp = Input()
        qtbot.addWidget(inp)
        inp.line_edit.setFocus()
        with qtbot.waitSignal(inp.returned, timeout=1000):
            qtbot.keyClick(inp.line_edit, Qt.Key.Key_Return)


class TestInputClearable:
    def test_clear_button_hidden_when_empty(self, qtbot):
        inp = Input(is_clearable=True)
        qtbot.addWidget(inp)
        # 空文本时按钮 opacity=0（隐藏态）
        assert not inp._clear_btn._visible

    def test_clear_button_visible_when_filled(self, qtbot):
        inp = Input(is_clearable=True)
        qtbot.addWidget(inp)
        inp.set_text("hello")
        assert inp._clear_btn._visible

    def test_clear_button_click_clears_text(self, qtbot):
        inp = Input(is_clearable=True)
        qtbot.addWidget(inp)
        inp.set_text("hello")
        inp._clear_btn.click()
        assert inp.text() == ""
