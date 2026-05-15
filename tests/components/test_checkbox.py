"""Checkbox / CheckboxGroup 组件测试"""

import pytest
from PySide6.QtCore import Qt

from hero_side_ui import Checkbox, CheckboxGroup


# ============================================================
# Checkbox
# ============================================================
class TestCheckboxInit:
    def test_default_params(self, qtbot):
        cb = Checkbox()
        qtbot.addWidget(cb)
        assert cb.text() == ""
        assert cb.isChecked() is False
        assert cb._color == "primary"
        assert cb._size == "md"
        assert cb._radius is None
        assert cb._line_through is False
        assert cb._is_disabled is False
        assert cb._is_invalid is False
        assert cb._is_indeterminate is False
        assert cb._theme_mode == "auto"

    def test_initial_selected(self, qtbot):
        cb = Checkbox("On", is_selected=True)
        qtbot.addWidget(cb)
        assert cb.isChecked() is True
        assert cb._fill_progress == 1.0

    def test_value_defaults_to_text(self, qtbot):
        cb = Checkbox("Hello")
        qtbot.addWidget(cb)
        assert cb.value() == "Hello"

    def test_explicit_value(self, qtbot):
        cb = Checkbox("Hello", value="hi")
        qtbot.addWidget(cb)
        assert cb.value() == "hi"


class TestCheckboxColors:
    @pytest.mark.parametrize("color", ["default", "primary", "secondary", "success", "warning", "danger"])
    def test_all_colors(self, qtbot, color):
        cb = Checkbox("x", color=color)
        qtbot.addWidget(cb)
        assert cb._color == color


class TestCheckboxSizes:
    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_all_sizes(self, qtbot, size):
        cb = Checkbox("x", size=size)
        qtbot.addWidget(cb)
        assert cb._size == size

    def test_sizehint_grows_with_size(self, qtbot):
        small = Checkbox("x", size="sm")
        large = Checkbox("x", size="lg")
        qtbot.addWidget(small)
        qtbot.addWidget(large)
        assert large.sizeHint().height() >= small.sizeHint().height()


class TestCheckboxRadius:
    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg", "full"])
    def test_all_radius(self, qtbot, radius):
        cb = Checkbox("x", radius=radius)
        qtbot.addWidget(cb)
        assert cb._radius == radius

    def test_full_radius_is_half_box(self, qtbot):
        cb = Checkbox("x", size="md", radius="full")
        qtbot.addWidget(cb)
        # md box = 20, full → 10
        assert cb._resolve_box_radius(20) == 10.0


class TestCheckboxStates:
    def test_disabled_state(self, qtbot):
        cb = Checkbox("x", is_disabled=True)
        qtbot.addWidget(cb)
        assert cb.isEnabled() is False

    def test_invalid_state(self, qtbot):
        cb = Checkbox("x", is_invalid=True)
        qtbot.addWidget(cb)
        assert cb._is_invalid is True

    def test_indeterminate_state(self, qtbot):
        cb = Checkbox("x", is_indeterminate=True)
        qtbot.addWidget(cb)
        assert cb._is_indeterminate is True

    def test_line_through_state(self, qtbot):
        cb = Checkbox("x", line_through=True, is_selected=True)
        qtbot.addWidget(cb)
        assert cb._line_through is True
        assert cb._line_progress == 1.0


class TestCheckboxSignals:
    def test_toggled_signal(self, qtbot):
        cb = Checkbox("x")
        qtbot.addWidget(cb)
        received = []
        cb.toggled.connect(received.append)
        cb.setChecked(True)
        assert received == [True]
        cb.setChecked(False)
        assert received == [True, False]

    def test_state_changed_drives_fill(self, qtbot):
        cb = Checkbox("x", disable_animation=True)
        qtbot.addWidget(cb)
        cb.setChecked(True)
        assert cb._fill_progress == 1.0
        cb.setChecked(False)
        assert cb._fill_progress == 0.0


class TestCheckboxDynamicAPI:
    def test_set_color(self, qtbot):
        cb = Checkbox("x")
        qtbot.addWidget(cb)
        cb.set_color("success")
        assert cb._color == "success"

    def test_set_size(self, qtbot):
        cb = Checkbox("x", size="sm")
        qtbot.addWidget(cb)
        cb.set_size("lg")
        assert cb._size == "lg"

    def test_set_radius(self, qtbot):
        cb = Checkbox("x")
        qtbot.addWidget(cb)
        cb.set_radius("full")
        assert cb._radius == "full"

    def test_set_theme(self, qtbot):
        cb = Checkbox("x")
        qtbot.addWidget(cb)
        cb.set_theme("dark")
        assert cb._theme == "dark"

    def test_set_line_through(self, qtbot):
        cb = Checkbox("x", is_selected=True)
        qtbot.addWidget(cb)
        cb.set_line_through(True)
        assert cb._line_through is True
        assert cb._line_progress == 1.0
        cb.set_line_through(False)
        assert cb._line_progress == 0.0

    def test_set_is_disabled(self, qtbot):
        cb = Checkbox("x")
        qtbot.addWidget(cb)
        cb.set_is_disabled(True)
        assert cb._is_disabled is True
        assert cb.isEnabled() is False

    def test_set_is_invalid(self, qtbot):
        cb = Checkbox("x")
        qtbot.addWidget(cb)
        cb.set_is_invalid(True)
        assert cb._is_invalid is True

    def test_set_is_indeterminate(self, qtbot):
        cb = Checkbox("x")
        qtbot.addWidget(cb)
        cb.set_is_indeterminate(True)
        assert cb._is_indeterminate is True

    def test_set_is_selected_alias(self, qtbot):
        cb = Checkbox("x")
        qtbot.addWidget(cb)
        cb.set_is_selected(True)
        assert cb.isChecked() is True
        assert cb.is_selected() is True


# ============================================================
# CheckboxGroup
# ============================================================
class TestCheckboxGroupBasic:
    def test_default_params(self, qtbot):
        g = CheckboxGroup()
        qtbot.addWidget(g)
        assert g._orientation == "vertical"
        assert g._color == "primary"
        assert g.value() == []

    def test_create_and_value(self, qtbot):
        g = CheckboxGroup()
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        g.create_checkbox("B", "b")
        g.create_checkbox("C", "c")
        assert g.value() == []
        g._checkboxes[0].setChecked(True)
        g._checkboxes[2].setChecked(True)
        assert g.value() == ["a", "c"]

    def test_default_value(self, qtbot):
        g = CheckboxGroup(default_value=["a", "c"])
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        g.create_checkbox("B", "b")
        g.create_checkbox("C", "c")
        assert g.value() == ["a", "c"]

    def test_set_value(self, qtbot):
        g = CheckboxGroup()
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        g.create_checkbox("B", "b")
        g.set_value(["b"])
        assert g.value() == ["b"]

    def test_value_changed_signal(self, qtbot):
        g = CheckboxGroup()
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        g.create_checkbox("B", "b")

        captured = []
        g.value_changed.connect(captured.append)
        g._checkboxes[0].setChecked(True)
        assert captured[-1] == ["a"]
        g._checkboxes[1].setChecked(True)
        assert captured[-1] == ["a", "b"]

    def test_color_broadcast(self, qtbot):
        g = CheckboxGroup(color="primary")
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        g.create_checkbox("B", "b")
        g.set_color("success")
        assert all(cb._color == "success" for cb in g._checkboxes)

    def test_size_broadcast(self, qtbot):
        g = CheckboxGroup(size="md")
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        g.set_size("lg")
        assert g._checkboxes[0]._size == "lg"

    def test_theme_broadcast(self, qtbot):
        g = CheckboxGroup()
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        g.set_theme("dark")
        assert g._checkboxes[0]._theme == "dark"

    def test_invalid_and_required(self, qtbot):
        g = CheckboxGroup(is_invalid=True, is_required=True,
                          label="L", error_message="Oops")
        qtbot.addWidget(g)
        assert g._is_invalid is True
        assert g._is_required is True

    @pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
    def test_orientation(self, qtbot, orientation):
        g = CheckboxGroup(orientation=orientation)
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        g.create_checkbox("B", "b")
        assert g._orientation == orientation


class TestCheckboxGroupCombinations:
    @pytest.mark.parametrize("color", ["default", "primary", "secondary", "success", "warning", "danger"])
    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_matrix(self, qtbot, color, size, theme):
        g = CheckboxGroup(color=color, size=size, theme=theme)
        qtbot.addWidget(g)
        g.create_checkbox("A", "a")
        cb = g._checkboxes[0]
        assert cb._color == color
        assert cb._size == size
        assert cb._theme == theme
