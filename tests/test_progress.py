"""Progress / CircularProgress 测试"""

import pytest

from hero_side_ui import Progress, CircularProgress


# ============================================================
# Progress
# ============================================================
class TestProgressInit:
    def test_default(self, qtbot):
        p = Progress()
        qtbot.addWidget(p)
        assert p.value() == 0
        assert p._min == 0 and p._max == 100
        assert p._color == "primary"
        assert p._size == "md"
        assert p._radius == "full"
        assert p._is_striped is False
        assert p._is_indeterminate is False
        assert p._is_disabled is False

    def test_value_clamp(self, qtbot):
        p = Progress(value=500, min_value=0, max_value=100)
        qtbot.addWidget(p)
        assert p.value() == 100

    def test_value_negative_clamp(self, qtbot):
        p = Progress(value=-10)
        qtbot.addWidget(p)
        assert p.value() == 0

    def test_progress_ratio(self, qtbot):
        p = Progress(value=25, max_value=100)
        qtbot.addWidget(p)
        assert abs(p._progress_ratio() - 0.25) < 1e-6

    def test_progress_ratio_custom_range(self, qtbot):
        p = Progress(value=5, min_value=0, max_value=10)
        qtbot.addWidget(p)
        assert abs(p._progress_ratio() - 0.5) < 1e-6


class TestProgressVariants:
    @pytest.mark.parametrize("color", ["default", "primary", "secondary", "success", "warning", "danger"])
    def test_colors(self, qtbot, color):
        p = Progress(color=color)
        qtbot.addWidget(p)
        assert p._color == color

    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_sizes(self, qtbot, size):
        p = Progress(size=size)
        qtbot.addWidget(p)
        assert p._size == size
        assert p._track_height() > 0

    @pytest.mark.parametrize("radius", ["none", "sm", "full"])
    def test_radius(self, qtbot, radius):
        p = Progress(radius=radius)
        qtbot.addWidget(p)
        assert p._radius == radius
        assert p._resolve_radius(12) >= 0

    def test_striped(self, qtbot):
        p = Progress(is_striped=True)
        qtbot.addWidget(p)
        assert p._is_striped is True

    def test_indeterminate(self, qtbot):
        p = Progress(is_indeterminate=True)
        qtbot.addWidget(p)
        assert p._is_indeterminate is True

    def test_disabled(self, qtbot):
        p = Progress(is_disabled=True)
        qtbot.addWidget(p)
        assert p._is_disabled is True


class TestProgressLabel:
    def test_no_label_no_value_hides_row(self, qtbot):
        p = Progress()
        qtbot.addWidget(p)
        assert p._label_row_widget.isVisibleTo(p) is False or not p._label_row_widget.isVisible()

    def test_label_shows_row(self, qtbot):
        p = Progress(label="Loading")
        qtbot.addWidget(p)
        p.show()
        assert p._label.text() == "Loading"

    def test_value_label_percentage(self, qtbot):
        p = Progress(value=33, show_value_label=True)
        qtbot.addWidget(p)
        p.show()
        assert "33" in p._value_label.text()

    def test_custom_formatter(self, qtbot):
        p = Progress(value=3, max_value=10, show_value_label=True,
                     value_label_formatter=lambda v, mn, mx: f"{int(v)}/{int(mx)}")
        qtbot.addWidget(p)
        p.show()
        assert p._value_label.text() == "3/10"


class TestProgressDynamicAPI:
    def test_set_value(self, qtbot):
        p = Progress(value=0, show_value_label=True, disable_animation=True)
        qtbot.addWidget(p)
        p.set_value(42)
        assert p.value() == 42

    def test_set_range(self, qtbot):
        p = Progress(value=50, max_value=100)
        qtbot.addWidget(p)
        p.set_range(0, 200)
        assert p._min == 0 and p._max == 200

    def test_set_color(self, qtbot):
        p = Progress()
        qtbot.addWidget(p)
        p.set_color("success")
        assert p._color == "success"

    def test_set_size(self, qtbot):
        p = Progress()
        qtbot.addWidget(p)
        p.set_size("lg")
        assert p._size == "lg"

    def test_set_is_striped(self, qtbot):
        p = Progress()
        qtbot.addWidget(p)
        p.set_is_striped(True)
        assert p._is_striped is True

    def test_set_is_indeterminate(self, qtbot):
        p = Progress()
        qtbot.addWidget(p)
        p.set_is_indeterminate(True)
        assert p._is_indeterminate is True
        p.set_is_indeterminate(False)
        assert p._is_indeterminate is False

    def test_set_theme(self, qtbot):
        p = Progress()
        qtbot.addWidget(p)
        p.set_theme("dark")
        assert p._theme == "dark"


# ============================================================
# CircularProgress
# ============================================================
class TestCircularProgressInit:
    def test_default(self, qtbot):
        cp = CircularProgress()
        qtbot.addWidget(cp)
        assert cp.value() == 0
        assert cp._color == "primary"
        assert cp._size == "md"
        assert cp._is_indeterminate is False

    @pytest.mark.parametrize("color", ["default", "primary", "secondary", "success", "warning", "danger"])
    def test_colors(self, qtbot, color):
        cp = CircularProgress(color=color)
        qtbot.addWidget(cp)
        assert cp._color == color

    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_sizes(self, qtbot, size):
        cp = CircularProgress(size=size)
        qtbot.addWidget(cp)
        assert cp._size == size
        # svg 应有固定尺寸
        assert cp._svg.width() > 0

    def test_stroke_override(self, qtbot):
        cp = CircularProgress(stroke_width=6.0)
        qtbot.addWidget(cp)
        assert cp._stroke_width() == 6.0

    def test_indeterminate(self, qtbot):
        cp = CircularProgress(is_indeterminate=True)
        qtbot.addWidget(cp)
        assert cp._is_indeterminate is True

    def test_disabled(self, qtbot):
        cp = CircularProgress(is_disabled=True)
        qtbot.addWidget(cp)
        assert cp._is_disabled is True


class TestCircularProgressDynamicAPI:
    def test_set_value(self, qtbot):
        cp = CircularProgress(value=0, disable_animation=True)
        qtbot.addWidget(cp)
        cp.set_value(80)
        assert cp.value() == 80

    def test_set_color(self, qtbot):
        cp = CircularProgress()
        qtbot.addWidget(cp)
        cp.set_color("danger")
        assert cp._color == "danger"

    def test_set_size(self, qtbot):
        cp = CircularProgress(size="sm")
        qtbot.addWidget(cp)
        cp.set_size("lg")
        assert cp._size == "lg"
        assert cp._svg.width() > 0

    def test_set_is_indeterminate(self, qtbot):
        cp = CircularProgress()
        qtbot.addWidget(cp)
        cp.set_is_indeterminate(True)
        assert cp._is_indeterminate is True
        cp.set_is_indeterminate(False)
        assert cp._is_indeterminate is False

    def test_set_theme(self, qtbot):
        cp = CircularProgress()
        qtbot.addWidget(cp)
        cp.set_theme("dark")
        assert cp._theme == "dark"
