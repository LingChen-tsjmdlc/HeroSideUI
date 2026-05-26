"""Radio / RadioGroup 组件测试"""

import pytest

from hero_side_ui import Radio, RadioGroup


# ============================================================
# Radio
# ============================================================
class TestRadioInit:
    def test_default_params(self, qtbot):
        r = Radio()
        qtbot.addWidget(r)
        assert r.text() == ""
        assert r.isChecked() is False
        assert r._color == "primary"
        assert r._size == "md"
        assert r._is_disabled is False
        assert r._is_invalid is False
        assert r._theme_mode == "auto"

    def test_initial_selected(self, qtbot):
        r = Radio("On", is_selected=True)
        qtbot.addWidget(r)
        assert r.isChecked() is True
        assert r._control_progress == 1.0

    def test_value_defaults_to_text(self, qtbot):
        r = Radio("Hello")
        qtbot.addWidget(r)
        assert r.value() == "Hello"

    def test_explicit_value(self, qtbot):
        r = Radio("Hello", value="hi")
        qtbot.addWidget(r)
        assert r.value() == "hi"

    def test_description(self, qtbot):
        r = Radio("Plan", description="Free tier")
        qtbot.addWidget(r)
        assert r.description() == "Free tier"


class TestRadioColors:
    @pytest.mark.parametrize(
        "color", ["default", "primary", "secondary", "success", "warning", "danger"]
    )
    def test_all_colors(self, qtbot, color):
        r = Radio("x", color=color)
        qtbot.addWidget(r)
        assert r._color == color

    def test_invalid_color_raises(self, qtbot):
        with pytest.raises(ValueError):
            Radio("x", color="rainbow")


class TestRadioSizes:
    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_all_sizes(self, qtbot, size):
        r = Radio("x", size=size)
        qtbot.addWidget(r)
        assert r._size == size

    def test_sizehint_grows_with_size(self, qtbot):
        small = Radio("x", size="sm")
        large = Radio("x", size="lg")
        qtbot.addWidget(small)
        qtbot.addWidget(large)
        assert large.sizeHint().height() >= small.sizeHint().height()

    def test_invalid_size_raises(self, qtbot):
        with pytest.raises(ValueError):
            Radio("x", size="huge")


class TestRadioStates:
    def test_disabled_state(self, qtbot):
        r = Radio("x", is_disabled=True)
        qtbot.addWidget(r)
        assert r.isEnabled() is False

    def test_invalid_state(self, qtbot):
        r = Radio("x", is_invalid=True)
        qtbot.addWidget(r)
        assert r._is_invalid is True


class TestRadioSignals:
    def test_toggled_signal(self, qtbot):
        r = Radio("x")
        qtbot.addWidget(r)
        received = []
        r.toggled.connect(received.append)
        r.setChecked(True)
        assert received == [True]
        r.setChecked(False)
        assert received == [True, False]

    def test_selected_signal_emits_value(self, qtbot):
        r = Radio("Hi", value="hi")
        qtbot.addWidget(r)
        captured = []
        r.selected.connect(captured.append)
        r.setChecked(True)  # 触发 selected
        r.setChecked(False)  # 取消不应再 emit selected
        assert captured == ["hi"]

    def test_disable_animation_drives_progress(self, qtbot):
        r = Radio("x", disable_animation=True)
        qtbot.addWidget(r)
        r.setChecked(True)
        assert r._control_progress == 1.0
        r.setChecked(False)
        assert r._control_progress == 0.0


class TestRadioDynamicAPI:
    def test_set_color(self, qtbot):
        r = Radio("x")
        qtbot.addWidget(r)
        r.set_color("success")
        assert r._color == "success"

    def test_set_size(self, qtbot):
        r = Radio("x", size="sm")
        qtbot.addWidget(r)
        r.set_size("lg")
        assert r._size == "lg"

    def test_set_theme(self, qtbot):
        r = Radio("x")
        qtbot.addWidget(r)
        r.set_theme("dark")
        assert r._theme == "dark"

    def test_set_description(self, qtbot):
        r = Radio("x")
        qtbot.addWidget(r)
        r.set_description("hello")
        assert r.description() == "hello"

    def test_set_is_disabled(self, qtbot):
        r = Radio("x")
        qtbot.addWidget(r)
        r.set_is_disabled(True)
        assert r._is_disabled is True
        assert r.isEnabled() is False

    def test_set_is_invalid(self, qtbot):
        r = Radio("x")
        qtbot.addWidget(r)
        r.set_is_invalid(True)
        assert r._is_invalid is True

    def test_set_is_selected_alias(self, qtbot):
        r = Radio("x")
        qtbot.addWidget(r)
        r.set_is_selected(True)
        assert r.isChecked() is True
        assert r.is_selected() is True

    def test_set_value(self, qtbot):
        r = Radio("Hello")
        qtbot.addWidget(r)
        r.set_value("world")
        assert r.value() == "world"


# ============================================================
# RadioGroup
# ============================================================
class TestRadioGroupBasic:
    def test_default_params(self, qtbot):
        g = RadioGroup()
        qtbot.addWidget(g)
        assert g._orientation == "vertical"
        assert g._color == "primary"
        assert g.value() is None

    def test_create_and_value(self, qtbot):
        g = RadioGroup()
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.create_radio("B", value="b")
        g.create_radio("C", value="c")
        assert g.value() is None
        g._radios[0].setChecked(True)
        assert g.value() == "a"

    def test_default_value(self, qtbot):
        g = RadioGroup(default_value="b")
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.create_radio("B", value="b")
        g.create_radio("C", value="c")
        assert g.value() == "b"

    def test_set_value(self, qtbot):
        g = RadioGroup()
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.create_radio("B", value="b")
        g.set_value("b")
        assert g.value() == "b"

    def test_value_changed_signal(self, qtbot):
        g = RadioGroup()
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.create_radio("B", value="b")

        captured = []
        g.value_changed.connect(captured.append)
        g._radios[0].setChecked(True)
        assert captured[-1] == "a"
        g._radios[1].setChecked(True)
        assert captured[-1] == "b"

    def test_mutual_exclusion(self, qtbot):
        """选中其中一个时其它自动取消"""
        g = RadioGroup()
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.create_radio("B", value="b")
        g._radios[0].setChecked(True)
        assert g._radios[0].isChecked() is True
        assert g._radios[1].isChecked() is False
        g._radios[1].setChecked(True)
        assert g._radios[0].isChecked() is False
        assert g._radios[1].isChecked() is True

    def test_color_broadcast(self, qtbot):
        g = RadioGroup(color="primary")
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.create_radio("B", value="b")
        g.set_color("success")
        assert all(r._color == "success" for r in g._radios)

    def test_size_broadcast(self, qtbot):
        g = RadioGroup(size="md")
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.set_size("lg")
        assert g._radios[0]._size == "lg"

    def test_theme_broadcast(self, qtbot):
        g = RadioGroup()
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.set_theme("dark")
        assert g._radios[0]._theme == "dark"

    def test_invalid_and_required(self, qtbot):
        g = RadioGroup(
            is_invalid=True, is_required=True, label="L", error_message="Oops"
        )
        qtbot.addWidget(g)
        assert g._is_invalid is True
        assert g._is_required is True

    @pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
    def test_orientation(self, qtbot, orientation):
        g = RadioGroup(orientation=orientation)
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.create_radio("B", value="b")
        assert g._orientation == orientation

    def test_set_orientation_switch(self, qtbot):
        g = RadioGroup(orientation="vertical")
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        g.create_radio("B", value="b")
        g.set_orientation("horizontal")
        assert g._orientation == "horizontal"
        # 子 radio 不应被销毁
        assert all(r.value() in ("a", "b") for r in g._radios)


class TestRadioGroupCombinations:
    @pytest.mark.parametrize(
        "color", ["default", "primary", "secondary", "success", "warning", "danger"]
    )
    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_matrix(self, qtbot, color, size, theme):
        g = RadioGroup(color=color, size=size, theme=theme)
        qtbot.addWidget(g)
        g.create_radio("A", value="a")
        r = g._radios[0]
        assert r._color == color
        assert r._size == size
        assert r._theme == theme
