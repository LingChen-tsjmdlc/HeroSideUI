"""DateInput 渲染层测试。

构造 / 参数遍历 / 键盘交互 / 信号 / API，走 pytest-qt。
纯逻辑（段序、状态机、值原语）见 test_date_input_logic.py。
"""

import pytest

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from hero_side_ui import DateInput
from hero_side_ui.themes import HEROUI_COLORS
from hero_side_ui.components.date_input._value import (
    parse_absolute_to_local,
    parse_date,
    parse_datetime,
    parse_zoned_datetime,
    today,
)


def _make(qtbot, **kwargs) -> DateInput:
    di = DateInput(**kwargs)
    qtbot.addWidget(di)
    return di


def _render(di: DateInput) -> str:
    """拼出段行当前显示的完整文本。"""
    parts = []
    for i in range(di._segment_layout.count()):
        w = di._segment_layout.itemAt(i).widget()
        if w is not None:
            parts.append(w.text())
    return "".join(parts)


def _show_active(qtbot, di: DateInput) -> None:
    """显示并激活窗口。

    段焦点断言必须让窗口成为 active window，否则 Qt 不会把键盘焦点真正
    交给子 widget，hasFocus() 恒为 False。
    """
    di.show()
    qtbot.waitExposed(di)
    di.activateWindow()
    di.raise_()
    qtbot.waitUntil(di.isActiveWindow, timeout=2000)


# ---------------------------------------------------------------- 构造


def test_construct_default(qtbot):
    di = _make(qtbot)
    assert di.value() is None


def test_construct_with_value(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-04"))
    assert di.value() == parse_date("2024-04-04")
    assert _render(di) == "04/04/2024"


def test_construct_with_placeholder_shows_hint(qtbot):
    di = _make(qtbot, placeholder_value=parse_date("1995-11-06"))
    assert _render(di) == "mm/dd/yyyy"
    assert di.value() is None


def test_construct_all_variants(qtbot):
    for variant in ("flat", "faded", "bordered", "underlined"):
        di = _make(qtbot, label="x", variant=variant)
        assert di is not None


def test_construct_all_colors(qtbot):
    for color in (
        "default",
        "primary",
        "secondary",
        "success",
        "warning",
        "danger",
    ):
        di = _make(qtbot, label="x", color=color)
        assert di is not None


def test_construct_all_sizes(qtbot):
    for size in ("sm", "md", "lg"):
        di = _make(qtbot, label="x", size=size)
        assert di is not None


def test_construct_all_radii(qtbot):
    for radius in ("none", "sm", "md", "lg", "full"):
        di = _make(qtbot, label="x", radius=radius)
        assert di is not None


def test_construct_all_label_placements(qtbot):
    for placement in ("inside", "outside", "outside-left", "outside-top"):
        di = _make(qtbot, label="x", label_placement=placement)
        assert di is not None


@pytest.mark.parametrize("granularity", ["day", "hour", "minute", "second"])
def test_construct_all_granularities(qtbot, granularity):
    di = _make(qtbot, label="x", granularity=granularity)
    assert di is not None


def test_invalid_granularity_rejected(qtbot):
    with pytest.raises(ValueError):
        DateInput(granularity="fortnight")


def test_construct_states(qtbot):
    for kwargs in (
        {"is_disabled": True},
        {"is_invalid": True, "error_message": "bad"},
        {"is_required": True},
        {"is_readonly": True},
        {"full_width": False},
        {"description": "hint"},
    ):
        di = _make(qtbot, label="x", **kwargs)
        assert di is not None


def test_out_of_range_value_is_invalid_on_construct(qtbot):
    """越界初始值应自动进入 invalid，不依赖外部传 is_invalid。"""
    di = _make(
        qtbot, value=parse_date("2024-04-03"), min_value=parse_date("2024-04-10")
    )
    assert di._is_invalid is True


# ---------------------------------------------------------------- 段结构


def test_segment_order_follows_locale(qtbot):
    en = _make(qtbot, locale="en_US")
    assert [s.seg_type for s in en._editable_segments()] == ["month", "day", "year"]

    de = _make(qtbot, locale="de_DE")
    assert [s.seg_type for s in de._editable_segments()] == ["day", "month", "year"]


def test_zoned_value_renders_timezone(qtbot):
    di = _make(
        qtbot,
        granularity="minute",
        value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
    )
    assert "PST" in _render(di)


def test_hide_time_zone(qtbot):
    di = _make(
        qtbot,
        granularity="minute",
        hide_time_zone=True,
        value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
    )
    assert "PST" not in _render(di)


def test_segment_qss_survives_theme_switch(qtbot):
    """主题切换后段的字色/padding/圆角不得被 Text 的主题自治覆盖。

    段继承 Text，若保留 theme="auto"，ThemeProvider 广播时
    Text._apply_color() 会 setStyleSheet 整体重写，把宿主按 color 决策的
    字色冲成默认前景色（暗色下即白字），并连带丢掉 padding / border-radius。
    """
    from hero_side_ui.core import ThemeProvider

    provider = ThemeProvider.instance()
    original = provider.current_theme
    try:
        # 先锁定起始主题，保证后续每一步都是"真实跨越变化"——
        # Text._apply_color() 有幂等守卫，主题值没变时不会重写 QSS，
        # 起始态与首个断言态相同会让本测试变成空测试。
        provider.set_mode("light")
        qtbot.wait(30)
        di = _make(qtbot, color="warning", value=parse_date("2024-04-04"))
        seg = di._segment_widgets[0]

        for theme in ("dark", "light", "dark"):
            provider.set_mode(theme)
            qtbot.wait(30)
            qss = seg.styleSheet()
            assert "padding-left" in qss, f"{theme}: padding 被覆盖丢失"
            assert "border-radius" in qss, f"{theme}: border-radius 被覆盖丢失"
            # 字色必须是 warning 色系，不能退回默认前景色
            expected = di._resolve_segment_text_colors(
                theme == "dark",
                HEROUI_COLORS["warning"],
                HEROUI_COLORS["default"],
            )[0]
            assert f"{expected.red()}, {expected.green()}, {expected.blue()}" in qss, (
                f"{theme}: 段字色被覆盖，实际 QSS={qss[:120]}"
            )
    finally:
        provider.set_mode(original)


def test_segments_never_clipped_across_state_changes(qtbot):
    """段与分隔符的实际宽度不得小于其 sizeHint。

    早期为模仿 HeroUI 的 `-ml-1` 曾用 setFixedWidth 硬收分隔符宽度，
    导致 "/" 字形被裁在窄框里，换色/hover 触发重绘时表现为字间距时紧时松。
    """
    di = _make(qtbot, value=parse_date("2024-04-04"), full_width=False)
    _show_active(qtbot, di)

    def assert_not_clipped(tag):
        qtbot.waitUntil(lambda: di._segment_row.width() > 0, timeout=1000)
        di._segment_row.layout().activate()
        for w in di._literal_widgets + di._segment_widgets:
            assert w.width() >= w.sizeHint().width(), (
                f"{tag}: {w.text()!r} 被裁 "
                f"(width={w.width()} < sizeHint={w.sizeHint().width()})"
            )

    assert_not_clipped("初始")
    for size in ("sm", "md", "lg"):
        di.set_size(size)
        for color in ("default", "warning", "primary"):
            di.set_color(color)
            qtbot.wait(20)
            assert_not_clipped(f"size={size} color={color}")


def test_timezone_segment_not_editable(qtbot):
    di = _make(
        qtbot,
        granularity="minute",
        value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
    )
    assert "timeZone" not in [s.seg_type for s in di._editable_segments()]


def test_international_calendar(qtbot):
    di = _make(
        qtbot,
        locale="hi_IN",
        calendar="indian",
        value=parse_absolute_to_local("2021-04-07T18:45:22Z"),
    )
    assert di is not None
    assert _render(di) != ""


# ---------------------------------------------------------------- 键盘


def test_typing_fills_segments_and_advances(qtbot):
    di = _make(qtbot)
    _show_active(qtbot, di)

    segs = di._editable_segments()
    segs[0].setFocus()
    for key in (Qt.Key.Key_1, Qt.Key.Key_2):
        QTest.keyClick(segs[0], key)
    assert segs[0].text() == "12"
    # 输满后焦点应落到下一段
    assert segs[1].hasFocus()


def test_typing_full_date_produces_value(qtbot):
    di = _make(qtbot)
    _show_active(qtbot, di)

    segs = di._editable_segments()
    segs[0].setFocus()
    for key in (
        Qt.Key.Key_1,
        Qt.Key.Key_2,
        Qt.Key.Key_2,
        Qt.Key.Key_5,
        Qt.Key.Key_2,
        Qt.Key.Key_0,
        Qt.Key.Key_2,
        Qt.Key.Key_4,
    ):
        QTest.keyClick(di.window().focusWidget() or segs[0], key)
    assert di.value() == parse_date("2024-12-25")


def test_arrow_up_down_changes_segment(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-04"))
    _show_active(qtbot, di)

    seg = di._editable_segments()[0]
    seg.setFocus()
    QTest.keyClick(seg, Qt.Key.Key_Up)
    assert seg.text() == "05"
    QTest.keyClick(seg, Qt.Key.Key_Down)
    assert seg.text() == "04"


def test_left_right_moves_focus(qtbot):
    di = _make(qtbot)
    _show_active(qtbot, di)

    segs = di._editable_segments()
    segs[0].setFocus()
    QTest.keyClick(segs[0], Qt.Key.Key_Right)
    assert segs[1].hasFocus()
    QTest.keyClick(segs[1], Qt.Key.Key_Left)
    assert segs[0].hasFocus()


def test_backspace_clears_segment(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-04"))
    _show_active(qtbot, di)

    seg = di._editable_segments()[0]
    seg.setFocus()
    QTest.keyClick(seg, Qt.Key.Key_Backspace)
    assert seg.text() == "mm"
    assert di.value() is None


def test_a_p_keys_toggle_day_period(qtbot):
    di = _make(
        qtbot,
        granularity="minute",
        value=parse_datetime("2024-04-04T09:30:00"),
    )
    _show_active(qtbot, di)

    period = next(
        s for s in di._editable_segments() if s.seg_type == "dayPeriod"
    )
    period.setFocus()
    QTest.keyClick(period, Qt.Key.Key_P)
    assert di.value().hour == 21
    QTest.keyClick(period, Qt.Key.Key_A)
    assert di.value().hour == 9


def test_readonly_ignores_typing(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-04"), is_readonly=True)
    _show_active(qtbot, di)

    seg = di._editable_segments()[0]
    seg.setFocus()
    QTest.keyClick(seg, Qt.Key.Key_Up)
    assert seg.text() == "04"


def test_disabled_segments_not_focusable(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-04"), is_disabled=True)
    assert di._editable_segments() == []


# ---------------------------------------------------------------- 信号


def test_value_changed_on_set_value(qtbot):
    di = _make(qtbot)
    with qtbot.waitSignal(di.value_changed, timeout=1000) as blocker:
        di.set_value(parse_date("2024-04-04"))
    assert blocker.args[0] == parse_date("2024-04-04")


def test_value_changed_on_clear(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-04"))
    with qtbot.waitSignal(di.value_changed, timeout=1000) as blocker:
        di.clear()
    assert blocker.args[0] is None


def test_value_changed_on_typing(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-04"))
    _show_active(qtbot, di)

    seg = di._editable_segments()[0]
    seg.setFocus()
    with qtbot.waitSignal(di.value_changed, timeout=1000):
        QTest.keyClick(seg, Qt.Key.Key_Up)


# ---------------------------------------------------------------- API


def test_set_value_and_clear(qtbot):
    di = _make(qtbot)
    di.set_value(parse_date("2024-04-04"))
    assert _render(di) == "04/04/2024"
    di.clear()
    assert _render(di) == "mm/dd/yyyy"


def test_set_granularity_rebuilds_segments(qtbot):
    di = _make(qtbot, granularity="day")
    assert "hour" not in [s.seg_type for s in di._editable_segments()]
    di.set_granularity("minute")
    assert "hour" in [s.seg_type for s in di._editable_segments()]


def test_set_granularity_preserves_value(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-04"))
    di.set_granularity("minute")
    v = di.value()
    assert (v.year, v.month, v.day) == (2024, 4, 4)


def test_set_locale_rebuilds_order(qtbot):
    di = _make(qtbot, locale="en_US")
    di.set_locale("de_DE")
    assert [s.seg_type for s in di._editable_segments()] == [
        "day",
        "month",
        "year",
    ]


def test_set_hour_cycle(qtbot):
    di = _make(qtbot, granularity="minute", value=parse_datetime("2024-04-04T13:00:00"))
    di.set_hour_cycle(24)
    assert "dayPeriod" not in [s.seg_type for s in di._editable_segments()]


def test_set_hide_time_zone(qtbot):
    di = _make(
        qtbot,
        granularity="minute",
        value=parse_zoned_datetime("2022-11-07T00:45[America/Los_Angeles]"),
    )
    di.set_hide_time_zone(True)
    assert "PST" not in _render(di)


def test_set_min_max_updates_invalid(qtbot):
    di = _make(qtbot, value=parse_date("2024-04-03"))
    assert di._is_invalid is False
    di.set_min_value(parse_date("2024-04-10"))
    assert di._is_invalid is True


def test_appearance_setters(qtbot):
    di = _make(qtbot, label="x")
    di.set_label("y")
    di.set_color("primary")
    di.set_variant("bordered")
    di.set_size("lg")
    di.set_radius("full")
    di.set_label_placement("outside")
    assert di._label_text == "y"
    assert di._color == "primary"
    assert di._variant == "bordered"
    assert di._size == "lg"
    assert di._radius == "full"


def test_state_setters(qtbot):
    di = _make(qtbot, label="x")
    di.set_is_disabled(True)
    assert di._is_disabled is True
    di.set_is_disabled(False)
    di.set_is_invalid(True)
    assert di._is_invalid is True
    di.set_is_required(True)
    assert di._is_required is True
    di.set_is_readonly(True)
    assert di._is_readonly is True


def test_explicit_invalid_survives_value_change(qtbot):
    """用户显式设的 is_invalid 不该被值合法性覆盖掉。"""
    di = _make(qtbot, label="x")
    di.set_is_invalid(True)
    di.set_value(parse_date("2024-04-04"))
    assert di._is_invalid is True


def test_helper_text_setters(qtbot):
    di = _make(qtbot, label="x")
    di.set_description("desc")
    assert di._description == "desc"
    di.set_error_message("err")
    assert di._error_message == "err"


def test_content_setters(qtbot):
    di = _make(qtbot, label="x")
    di.set_start_content("heroicons--check-solid")
    di.set_end_content("heroicons--check-solid")
    assert di._start_content is not None
    assert di._end_content is not None


def test_width_takeover(qtbot):
    di = _make(qtbot, label="x")
    di.set_width(200)
    assert di._user_width_locked is True
    assert di.width() == 200


def test_theme_setter(qtbot):
    di = _make(qtbot, label="x")
    di.set_theme("dark")
    assert di._theme == "dark"
    di.set_theme("light")
    assert di._theme == "light"


def test_min_max_with_today(qtbot):
    di = _make(qtbot, label="x", min_value=today())
    assert di is not None
