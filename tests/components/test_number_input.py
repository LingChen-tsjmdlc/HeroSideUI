"""NumberInput 组件测试。

格式化/解析/夹取等纯逻辑与渲染/键盘/滚轮/信号测试合并在本文件，
按"逻辑 / 构造 / 步进 / 提交与夹取 / 状态与信号"分节，风格对齐
test_time_input.py。
"""

import pytest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from hero_side_ui import NumberInput


def _make(qtbot, **kwargs) -> NumberInput:
    ni = NumberInput(**kwargs)
    qtbot.addWidget(ni)
    return ni


def _show_active(qtbot, ni: NumberInput) -> None:
    ni.show()
    qtbot.waitExposed(ni)
    ni.activateWindow()
    ni.raise_()
    qtbot.waitUntil(ni.isActiveWindow, timeout=2000)


# ---------------------------------------------------------------- 逻辑：格式化


def test_format_grouping_and_fraction():
    ni = NumberInput()
    assert ni._format_number(1234.5) == "1,234.5"
    assert ni._format_number(1234567.0) == "1,234,567"
    # Intl 默认最多 3 位小数，超出四舍五入
    assert ni._format_number(1.23456) == "1.235"


def test_format_no_grouping():
    ni = NumberInput(format_options={"use_grouping": False})
    assert ni._format_number(1234.5) == "1234.5"


def test_format_minimum_fraction_digits():
    ni = NumberInput(format_options={"minimum_fraction_digits": 2})
    assert ni._format_number(5.0) == "5.00"
    assert ni._format_number(5.678) == "5.678"


def test_format_percent_and_currency():
    ni_p = NumberInput(format_options={"style": "percent"})
    assert ni_p._format_number(12.5) == "12.5%"
    ni_c = NumberInput(format_options={"style": "currency", "currency": "CNY"})
    assert ni_c._format_number(1234.5) == "¥1,234.50"
    ni_k = NumberInput(format_options={"style": "currency", "currency": "XYZ"})
    assert ni_k._format_number(3.0) == "XYZ 3.00"


def test_parse_strips_symbols():
    ni_c = NumberInput(format_options={"style": "currency", "currency": "CNY"})
    assert ni_c._parse_number("¥1,234.50") == 1234.5
    ni_p = NumberInput(format_options={"style": "percent"})
    assert ni_p._parse_number("12.5%") == 12.5
    ni = NumberInput()
    assert ni._parse_number("1,234") == 1234.0
    assert ni._parse_number("") is None
    assert ni._parse_number("abc") is None
    assert ni._parse_number("-") is None
    assert ni._parse_number("-12.5") == -12.5


def test_zero_step_rejected():
    with pytest.raises(ValueError):
        NumberInput(step=0)
    ni = NumberInput()
    with pytest.raises(ValueError):
        ni.set_step(0)


# ---------------------------------------------------------------- 构造


def test_construct_default(qtbot):
    ni = _make(qtbot)
    assert ni.value() is None
    assert ni.objectName() == "heroNumberInput"
    assert ni._step == 1.0


def test_construct_with_value_formats(qtbot):
    ni = _make(qtbot, value=1234.5)
    assert ni.text() == "1,234.5"
    assert ni.value() == 1234.5


def test_stepper_visible_by_default_and_hidden_when_hide(qtbot):
    ni = _make(qtbot)
    assert not ni._stepper.isHidden()
    ni2 = _make(qtbot, hide_stepper=True)
    assert ni2._stepper.isHidden()


def test_construct_all_variants(qtbot):
    for variant in ("flat", "faded", "bordered", "underlined"):
        assert _make(qtbot, label="x", variant=variant) is not None


def test_construct_all_colors(qtbot):
    for color in (
        "default",
        "primary",
        "secondary",
        "success",
        "warning",
        "danger",
    ):
        assert _make(qtbot, label="x", color=color) is not None


def test_construct_all_sizes(qtbot):
    for size in ("sm", "md", "lg"):
        assert _make(qtbot, label="x", size=size) is not None


def test_min_width_uses_number_token(qtbot):
    # 数字内容短，最小宽度走 NumberInput 专属 token（120/140/160），不是文本的 240/260/300
    from hero_side_ui.themes import NUMBER_INPUT_MIN_WIDTHS

    for size in ("sm", "md", "lg"):
        ni = _make(qtbot, label="x", size=size)
        expected = NUMBER_INPUT_MIN_WIDTHS[size]
        assert ni.minimumWidth() == expected
        assert ni._wrapper.minimumWidth() == expected
        assert expected < 240


def test_min_width_user_locked_not_overridden(qtbot):
    # 用户显式接管宽度后，restyle 不得用 token 抬高最小宽度
    ni = _make(qtbot, label="x")
    ni.setFixedWidth(80)
    ni.set_color("primary")  # 触发一次 _apply_styles
    assert ni.minimumWidth() == 80


# ---------------------------------------------------------------- 步进


def test_stepper_click_steps(qtbot):
    ni = _make(qtbot, value=5.0, step=2)
    ni._stepper._up_btn.click()
    assert ni.value() == 7.0
    ni._stepper._down_btn.click()
    assert ni.value() == 5.0


def test_keyboard_up_down_steps(qtbot):
    ni = _make(qtbot, value=5.0)
    _show_active(qtbot, ni)

    ni.line_edit.setFocus()
    QTest.keyClick(ni.line_edit, Qt.Key.Key_Up)
    assert ni.value() == 6.0
    QTest.keyClick(ni.line_edit, Qt.Key.Key_Down)
    assert ni.value() == 5.0


def test_wheel_steps_when_focused(qtbot):
    ni = _make(qtbot, value=5.0)
    _show_active(qtbot, ni)

    ni.line_edit.setFocus()
    # 模拟滚轮事件发给 line_edit（pixelDelta/angleDelta 必须 QPoint，phase 用 ScrollUpdate）
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPoint, QPointF

    pos = QPointF(ni.line_edit.rect().center())
    up = QWheelEvent(
        pos, QPointF(ni.line_edit.mapToGlobal(ni.line_edit.rect().center())),
        QPoint(0, 0), QPoint(0, 120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate, False,
    )
    ni.eventFilter(ni.line_edit, up)
    assert ni.value() == 6.0


def test_wheel_disabled_prop(qtbot):
    ni = _make(qtbot, value=5.0, is_wheel_disabled=True)
    _show_active(qtbot, ni)

    ni.line_edit.setFocus()
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPoint, QPointF

    pos = QPointF(ni.line_edit.rect().center())
    ev = QWheelEvent(
        pos, QPointF(ni.line_edit.mapToGlobal(ni.line_edit.rect().center())),
        QPoint(0, 0), QPoint(0, 120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate, False,
    )
    ni.eventFilter(ni.line_edit, ev)
    assert ni.value() == 5.0


def test_step_from_empty_starts_at_zero(qtbot):
    ni = _make(qtbot)
    ni._step_by(1)
    assert ni.value() == 1.0
    ni._step_by(-1)
    ni._step_by(-1)
    assert ni.value() == -1.0


def test_step_from_empty_starts_at_nearest_bound(qtbot):
    # 0 不在值域内时从最近边界起步
    ni = _make(qtbot, min_value=10.0, max_value=20.0)
    ni._step_by(1)
    assert ni.value() == 11.0
    ni2 = _make(qtbot, min_value=-20.0, max_value=-10.0)
    ni2._step_by(-1)
    assert ni2.value() == -11.0


def test_step_float_accumulation_clean(qtbot):
    ni = _make(qtbot, value=0.0, step=0.1)
    for _ in range(3):
        ni._step_by(1)
    assert ni.value() == pytest.approx(0.3)


def test_step_clamped_to_range(qtbot):
    ni = _make(qtbot, value=9.5, min_value=0.0, max_value=10.0, step=2.0)
    ni._step_by(1)
    assert ni.value() == 10.0


# ---------------------------------------------------------------- 提交与夹取


def test_commit_formats_text(qtbot):
    ni = _make(qtbot)
    ni.set_text("1234.5")
    ni._on_commit_text()
    assert ni.text() == "1,234.5"


def test_commit_clamps_to_range(qtbot):
    ni = _make(qtbot, min_value=0.0, max_value=100.0)
    ni.set_text("999999")
    ni._on_commit_text()
    assert ni.text() == "100"
    assert ni.value() == 100.0


def test_commit_invalid_text_marks_invalid(qtbot):
    ni = _make(qtbot)
    ni.set_text("abc")
    ni._on_commit_text()
    assert ni._auto_invalid
    assert ni._is_invalid
    assert ni.value() is None
    # 用户不改写输入：文本原样保留
    assert ni.text() == "abc"


def test_fixing_text_clears_auto_invalid(qtbot):
    ni = _make(qtbot)
    ni.set_text("abc")
    ni._on_commit_text()
    assert ni._auto_invalid
    ni.set_text("42")
    assert not ni._auto_invalid
    assert not ni._is_invalid
    assert ni.value() == 42.0


def test_set_min_max_resyncs_value(qtbot):
    ni = _make(qtbot, value=50.0)
    ni.set_max_value(10.0)
    assert ni.value() == 10.0
    ni.set_min_value(5.0)
    assert ni.value() == 10.0
    # 新值域 20~30：10 拉回新下界
    ni.set_min_value(20.0)
    ni.set_max_value(30.0)
    assert ni.value() == 20.0


def test_escape_clears_when_clearable(qtbot):
    ni = _make(qtbot, value=5.0, is_clearable=True)
    _show_active(qtbot, ni)

    ni.line_edit.setFocus()
    QTest.keyClick(ni.line_edit, Qt.Key.Key_Escape)
    assert ni.text() == ""
    assert ni.value() is None


def test_escape_ignores_when_not_clearable(qtbot):
    ni = _make(qtbot, value=5.0)
    _show_active(qtbot, ni)

    ni.line_edit.setFocus()
    QTest.keyClick(ni.line_edit, Qt.Key.Key_Escape)
    assert ni.text() == "5"


# ---------------------------------------------------------------- 状态与信号


def test_value_changed_signal(qtbot):
    ni = _make(qtbot)
    seen = []
    ni.value_changed.connect(seen.append)
    ni.set_text("42")
    assert seen[-1] == 42.0
    ni.set_text("")
    assert seen[-1] is None
    ni.set_text("abc")
    assert seen[-1] is None


def test_no_duplicate_value_changed(qtbot):
    ni = _make(qtbot, value=5.0)
    seen = []
    ni.value_changed.connect(seen.append)
    ni._step_by(1)
    ni._step_by(1)
    assert seen == [6.0, 7.0]


def test_disabled_blocks_stepping(qtbot):
    ni = _make(qtbot, value=5.0, is_disabled=True)
    assert not ni._stepper._up_btn.isEnabled()
    ni._step_by(1)
    assert ni.value() == 5.0
    ni.set_text("8")
    # 直接改文本仍可解析（disabled 只挡交互步进），提交时数值照常
    assert ni.value() == 8.0


def test_readonly_blocks_stepping(qtbot):
    ni = _make(qtbot, value=5.0, is_readonly=True)
    assert not ni._stepper._up_btn.isEnabled()
    ni._step_by(1)
    assert ni.value() == 5.0


def test_disabled_toggles_stepper_enabled(qtbot):
    ni = _make(qtbot, value=5.0)
    assert ni._stepper._up_btn.isEnabled()
    ni.set_is_disabled(True)
    assert not ni._stepper._up_btn.isEnabled()
    ni.set_is_disabled(False)
    assert ni._stepper._up_btn.isEnabled()


def test_set_value_and_clear(qtbot):
    ni = _make(qtbot)
    ni.set_value(7.25)
    assert ni.text() == "7.25"
    assert ni.value() == 7.25
    ni.set_value(None)
    assert ni.text() == ""
    assert ni.value() is None


def test_user_invalid_not_overridden(qtbot):
    ni = _make(qtbot, value=5.0, is_invalid=True)
    assert ni._is_invalid
    ni.set_text("42")
    # 用户显式设的 invalid 不被自动逻辑覆盖
    assert ni._is_invalid


def test_line_edit_proxy_still_works(qtbot):
    ni = _make(qtbot, value=1.5)
    # Input 既有代理方法/属性继续可用
    assert ni.text() == "1.5"
    ni.set_placeholder("Num")
    assert ni.line_edit.placeholderText() == "Num"
