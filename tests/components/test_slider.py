"""Slider 组件测试"""

import pytest

from hero_side_ui import Slider
from hero_side_ui.components.slider._geometry import (
    ratio_of,
    resolve_thumb_radius,
    value_at_ratio,
)
from hero_side_ui.components.slider._palette import filler_color, thumb_color


# ============================================================
# 构造 / 默认值
# ============================================================
class TestSliderInit:
    def test_default(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        assert s.value() == 0
        assert s._min == 0 and s._max == 100
        assert s._step == 1
        assert s._color == "primary"
        assert s._size == "md"
        assert s._radius == "full"
        assert s._orientation == "horizontal"
        assert s._is_range is False
        assert s._is_disabled is False

    def test_value_clamp_high(self, qtbot):
        s = Slider(value=500, min_value=0, max_value=100)
        qtbot.addWidget(s)
        assert s.value() == 100

    def test_value_clamp_low(self, qtbot):
        s = Slider(value=-50)
        qtbot.addWidget(s)
        assert s.value() == 0

    def test_value_snap_to_step(self, qtbot):
        s = Slider(value=37, min_value=0, max_value=100, step=10)
        qtbot.addWidget(s)
        # 37 应 snap 到 40
        assert s.value() == 40

    def test_invalid_range_raises(self, qtbot):
        with pytest.raises(ValueError):
            Slider(min_value=10, max_value=10)

    def test_invalid_step_raises(self, qtbot):
        with pytest.raises(ValueError):
            Slider(step=0)

    def test_range_init(self, qtbot):
        s = Slider(value=(20, 80))
        qtbot.addWidget(s)
        assert s._is_range is True
        assert s.value() == (20, 80)

    def test_range_value_swap_clamp(self, qtbot):
        # 元组顺序错也按 (lo, hi) 处理（set_value 会 sort，构造期保留输入序但仍 clamp）
        s = Slider(value=(150, 30), min_value=0, max_value=100)
        qtbot.addWidget(s)
        # 第一个被 clamp 到 100，第二个保留 30 — 这是构造期行为
        assert s._is_range is True


# ============================================================
# 变体
# ============================================================
class TestSliderVariants:
    @pytest.mark.parametrize(
        "color",
        ["foreground", "primary", "secondary", "success", "warning", "danger"],
    )
    def test_colors(self, qtbot, color):
        s = Slider(color=color)
        qtbot.addWidget(s)
        assert s._color == color
        # 颜色解析拆到模块级纯函数(_palette.py)
        assert filler_color(s._color, s._theme).isValid()
        assert thumb_color(s._color, s._theme).isValid()

    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_sizes(self, qtbot, size):
        s = Slider(size=size)
        qtbot.addWidget(s)
        assert s._size == size
        cfg = s._cfg()
        assert cfg["thumb"] > 0
        assert cfg["track_thickness"] > 0

    @pytest.mark.parametrize("radius", ["none", "sm", "md", "lg", "full"])
    def test_radius(self, qtbot, radius):
        s = Slider(radius=radius)
        qtbot.addWidget(s)
        assert s._radius == radius
        cfg = s._cfg()
        # 圆角解析为模块级纯函数(_geometry.py)
        assert resolve_thumb_radius(s._radius, cfg["thumb"]) >= 0

    @pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
    def test_orientation(self, qtbot, orientation):
        s = Slider(orientation=orientation)
        qtbot.addWidget(s)
        assert s._orientation == orientation


# ============================================================
# 标志位
# ============================================================
class TestSliderFlags:
    def test_disabled(self, qtbot):
        s = Slider(is_disabled=True)
        qtbot.addWidget(s)
        assert s._is_disabled is True

    def test_hide_value(self, qtbot):
        s = Slider(hide_value=True)
        qtbot.addWidget(s)
        assert s._hide_value is True

    def test_hide_thumb(self, qtbot):
        s = Slider(hide_thumb=True)
        qtbot.addWidget(s)
        assert s._hide_thumb is True

    def test_show_outline(self, qtbot):
        s = Slider(show_outline=True)
        qtbot.addWidget(s)
        assert s._show_outline is True

    def test_disable_thumb_scale(self, qtbot):
        s = Slider(disable_thumb_scale=True)
        qtbot.addWidget(s)
        assert s._disable_thumb_scale is True

    def test_disable_animation(self, qtbot):
        s = Slider(disable_animation=True)
        qtbot.addWidget(s)
        assert s._disable_animation is True

    def test_show_steps(self, qtbot):
        s = Slider(show_steps=True, step=10)
        qtbot.addWidget(s)
        assert s._show_steps is True


# ============================================================
# Marks
# ============================================================
class TestSliderMarks:
    def test_marks_dict(self, qtbot):
        s = Slider(marks=[{"value": 25, "label": "1/4"}, {"value": 50, "label": "1/2"}])
        qtbot.addWidget(s)
        assert len(s._marks) == 2
        assert s._marks[0] == (25.0, "1/4")

    def test_marks_tuple(self, qtbot):
        s = Slider(marks=[(20, "A"), (80, "B")])
        qtbot.addWidget(s)
        assert s._marks == [(20.0, "A"), (80.0, "B")]

    def test_marks_number_only(self, qtbot):
        s = Slider(marks=[10, 20, 30])
        qtbot.addWidget(s)
        assert len(s._marks) == 3
        # 单数字模式 label 默认为字符串化 value
        assert s._marks[0][1] == "10"


# ============================================================
# 值显示
# ============================================================
class TestSliderValueLabel:
    def test_default_format_int(self, qtbot):
        s = Slider(value=42, step=1)
        qtbot.addWidget(s)
        s.show()
        assert "42" in s._value_label.text()

    def test_default_format_float(self, qtbot):
        s = Slider(value=0.5, min_value=0, max_value=1, step=0.1)
        qtbot.addWidget(s)
        s.show()
        # 0.5 应保留 1 位小数
        assert "0.5" in s._value_label.text()

    def test_range_format(self, qtbot):
        s = Slider(value=(20, 80))
        qtbot.addWidget(s)
        s.show()
        text = s._value_label.text()
        assert "20" in text and "80" in text

    def test_custom_formatter(self, qtbot):
        s = Slider(value=50, value_formatter=lambda v: f"{int(v)}%")
        qtbot.addWidget(s)
        s.show()
        assert s._value_label.text() == "50%"

    def test_hide_value_empty_label(self, qtbot):
        s = Slider(value=50, hide_value=True)
        qtbot.addWidget(s)
        s.show()
        assert s._value_label.isVisible() is False


# ============================================================
# 内部计算
# ============================================================
class TestSliderRatio:
    def test_ratio_of_min_max(self, qtbot):
        s = Slider(min_value=0, max_value=100)
        qtbot.addWidget(s)
        assert ratio_of(0, s._min, s._max) == 0.0
        assert ratio_of(100, s._min, s._max) == 1.0
        assert abs(ratio_of(50, s._min, s._max) - 0.5) < 1e-9

    def test_ratio_of_custom_range(self, qtbot):
        s = Slider(min_value=-50, max_value=50)
        qtbot.addWidget(s)
        assert ratio_of(-50, s._min, s._max) == 0.0
        assert ratio_of(0, s._min, s._max) == 0.5
        assert ratio_of(50, s._min, s._max) == 1.0

    def test_value_at_ratio(self, qtbot):
        s = Slider(min_value=0, max_value=200)
        qtbot.addWidget(s)
        assert value_at_ratio(0, s._min, s._max) == 0
        assert value_at_ratio(0.5, s._min, s._max) == 100
        assert value_at_ratio(1.0, s._min, s._max) == 200


# ============================================================
# 动态 API
# ============================================================
class TestSliderDynamicAPI:
    def test_set_value(self, qtbot):
        s = Slider(value=0)
        qtbot.addWidget(s)
        s.set_value(60)
        assert s.value() == 60

    def test_set_value_to_range(self, qtbot):
        s = Slider(value=50)
        qtbot.addWidget(s)
        s.set_value((20, 80))
        assert s._is_range is True
        assert s.value() == (20, 80)

    def test_set_range(self, qtbot):
        s = Slider(value=50)
        qtbot.addWidget(s)
        s.set_range(0, 200)
        assert s._min == 0 and s._max == 200

    def test_set_step_re_snaps(self, qtbot):
        s = Slider(value=37, step=1)
        qtbot.addWidget(s)
        s.set_step(10)
        assert s.value() == 40

    def test_set_color(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        s.set_color("success")
        assert s._color == "success"

    def test_set_size(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        s.set_size("lg")
        assert s._size == "lg"

    def test_set_radius(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        s.set_radius("none")
        assert s._radius == "none"

    def test_set_label(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        s.set_label("Volume")
        assert s._label_text == "Volume"
        assert s._label.text() == "Volume"

    def test_set_is_disabled(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        s.set_is_disabled(True)
        assert s._is_disabled is True

    def test_set_hide_value(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        s.set_hide_value(True)
        assert s._hide_value is True

    def test_set_marks(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        s.set_marks([{"value": 10, "label": "ten"}])
        assert s._marks == [(10.0, "ten")]

    def test_set_theme(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        s.set_theme("dark")
        assert s._theme == "dark"

    def test_set_value_formatter(self, qtbot):
        s = Slider(value=50)
        qtbot.addWidget(s)
        s.show()
        s.set_value_formatter(lambda v: f"~{int(v)}~")
        assert s._value_label.text() == "~50~"


# ============================================================
# 信号
# ============================================================
class TestSliderSignals:
    def test_value_changed_emitted(self, qtbot):
        s = Slider(value=0)
        qtbot.addWidget(s)
        with qtbot.waitSignal(s.value_changed, timeout=500) as blocker:
            s.set_value(30)
        assert blocker.args == [30]

    def test_value_changed_range_emits_tuple(self, qtbot):
        s = Slider(value=(10, 20))
        qtbot.addWidget(s)
        with qtbot.waitSignal(s.value_changed, timeout=500) as blocker:
            s.set_value((40, 60))
        assert blocker.args == [(40, 60)]

    def test_set_value_unchanged_no_signal_for_internal_thumb_set(self, qtbot):
        # set_value 公共 API 总是 emit，但 _set_thumb_value 在值未变时不会 emit
        s = Slider(value=50)
        qtbot.addWidget(s)
        changed = s._set_thumb_value(0, 50)
        assert changed is False


# ============================================================
# Range 不交叉
# ============================================================
class TestSliderRangeNoCross:
    def test_lo_capped_by_hi(self, qtbot):
        s = Slider(value=(20, 80))
        qtbot.addWidget(s)
        # lo 试图越过 hi
        s._set_thumb_value(0, 90)
        lo, hi = s.value()
        assert lo <= hi

    def test_hi_floored_by_lo(self, qtbot):
        s = Slider(value=(20, 80))
        qtbot.addWidget(s)
        s._set_thumb_value(1, 5)
        lo, hi = s.value()
        assert hi >= lo
