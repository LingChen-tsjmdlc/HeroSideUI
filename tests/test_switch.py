"""Switch 组件测试"""

import pytest
from PySide6.QtCore import Qt

from hero_side_ui import Switch


# ============================================================
# 初始化
# ============================================================
class TestSwitchInit:
    def test_default_params(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        assert s.text() == ""
        assert s.isChecked() is False
        assert s.is_selected() is False
        assert s._color == "primary"
        assert s._size == "md"
        assert s._is_disabled is False
        assert s._is_read_only is False
        assert s._theme_mode == "auto"
        assert s.isCheckable() is True

    def test_with_text(self, qtbot):
        s = Switch("Airplane mode")
        qtbot.addWidget(s)
        assert s.text() == "Airplane mode"

    def test_initial_selected(self, qtbot):
        s = Switch(is_selected=True)
        qtbot.addWidget(s)
        assert s.isChecked() is True
        assert s._thumb_t == 1.0

    def test_initial_unselected_thumb_t(self, qtbot):
        s = Switch(is_selected=False)
        qtbot.addWidget(s)
        assert s._thumb_t == 0.0


# ============================================================
# 颜色 / 尺寸
# ============================================================
class TestSwitchColors:
    @pytest.mark.parametrize(
        "color",
        ["default", "primary", "secondary", "success", "warning", "danger"],
    )
    def test_all_colors(self, qtbot, color):
        s = Switch(is_selected=True, color=color)
        qtbot.addWidget(s)
        assert s._color == color


class TestSwitchSizes:
    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_all_sizes(self, qtbot, size):
        s = Switch(size=size)
        qtbot.addWidget(s)
        assert s._size == size

    def test_sizehint_grows_with_size(self, qtbot):
        small = Switch(size="sm")
        large = Switch(size="lg")
        qtbot.addWidget(small)
        qtbot.addWidget(large)
        assert large.sizeHint().width() > small.sizeHint().width()
        assert large.sizeHint().height() >= small.sizeHint().height()

    def test_text_extends_width(self, qtbot):
        no_text = Switch()
        with_text = Switch("Some label")
        qtbot.addWidget(no_text)
        qtbot.addWidget(with_text)
        assert with_text.sizeHint().width() > no_text.sizeHint().width()


# ============================================================
# 状态
# ============================================================
class TestSwitchStates:
    def test_disabled_state(self, qtbot):
        s = Switch(is_disabled=True)
        qtbot.addWidget(s)
        assert s.isEnabled() is False
        assert s._is_disabled is True

    def test_read_only_state(self, qtbot):
        s = Switch(is_read_only=True)
        qtbot.addWidget(s)
        assert s._is_read_only is True

    def test_read_only_does_not_toggle_on_click(self, qtbot):
        s = Switch(is_read_only=True)
        qtbot.addWidget(s)
        s.show()
        qtbot.waitExposed(s)
        assert s.isChecked() is False
        qtbot.mouseClick(s, Qt.MouseButton.LeftButton)
        assert s.isChecked() is False

    def test_disabled_does_not_toggle_on_click(self, qtbot):
        s = Switch(is_disabled=True)
        qtbot.addWidget(s)
        s.show()
        qtbot.waitExposed(s)
        assert s.isChecked() is False
        qtbot.mouseClick(s, Qt.MouseButton.LeftButton)
        assert s.isChecked() is False


# ============================================================
# 信号
# ============================================================
class TestSwitchSignals:
    def test_toggled_signal(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        received = []
        s.toggled.connect(received.append)
        s.setChecked(True)
        assert received == [True]
        s.setChecked(False)
        assert received == [True, False]

    def test_selected_changed_signal(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        received = []
        s.selected_changed.connect(received.append)
        s.setChecked(True)
        s.setChecked(False)
        assert received == [True, False]

    def test_toggle_updates_thumb_t_without_animation(self, qtbot):
        s = Switch(disable_animation=True)
        qtbot.addWidget(s)
        s.setChecked(True)
        assert s._thumb_t == 1.0
        s.setChecked(False)
        assert s._thumb_t == 0.0


# ============================================================
# 动态 API
# ============================================================
class TestSwitchDynamicAPI:
    def test_set_color(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        s.set_color("success")
        assert s._color == "success"

    def test_set_size(self, qtbot):
        s = Switch(size="sm")
        qtbot.addWidget(s)
        s.set_size("lg")
        assert s._size == "lg"

    def test_set_is_disabled(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        s.set_is_disabled(True)
        assert s._is_disabled is True
        assert s.isEnabled() is False

    def test_set_is_read_only(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        s.set_is_read_only(True)
        assert s._is_read_only is True

    def test_set_is_selected_alias(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        s.set_is_selected(True)
        assert s.isChecked() is True
        assert s.is_selected() is True

    def test_set_theme(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        s.set_theme("dark")
        assert s._theme == "dark"
        s.set_theme("light")
        assert s._theme == "light"

    def test_set_start_end_thumb_icon(self, qtbot):
        s = Switch()
        qtbot.addWidget(s)
        svg = '<svg xmlns="http://www.w3.org/2000/svg"/>'
        s.set_start_content(svg)
        s.set_end_content(svg)
        s.set_thumb_icon(svg)
        assert s._start_content == svg
        assert s._end_content == svg
        assert s._thumb_icon == svg


# ============================================================
# 主题 + 颜色 + 尺寸矩阵
# ============================================================
class TestSwitchMatrix:
    @pytest.mark.parametrize(
        "color",
        ["default", "primary", "secondary", "success", "warning", "danger"],
    )
    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_all_combinations_construct(self, qtbot, color, size, theme):
        s = Switch(is_selected=True, color=color, size=size, theme=theme)
        qtbot.addWidget(s)
        assert s._color == color
        assert s._size == size
        assert s._theme == theme
