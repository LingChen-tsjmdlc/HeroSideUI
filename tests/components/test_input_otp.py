"""InputOtp 组件测试"""

from __future__ import annotations

from hero_side_ui import InputOtp
from hero_side_ui.themes import INPUT_OTP_SIZES


class TestInputOtpInit:
    """构造参数与默认值"""

    def test_default_no_args(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        assert otp._length == 4
        assert otp.value() == ""
        assert otp._variant == "flat"
        assert otp._color == "default"
        assert otp._size == "md"
        assert otp._radius == "md"
        assert otp._allowed_keys == "^[0-9]*$"
        assert otp._text_align == "center"
        assert otp._type == "text"
        assert otp._is_invalid is False
        assert otp._is_read_only is False
        assert otp._is_disabled is False

    def test_custom_params(self, qtbot):
        otp = InputOtp(
            6,
            allowed_keys="^[A-F]*$",
            variant="bordered",
            color="primary",
            size="lg",
            radius="full",
            value="AB",
            description="Enter code",
            text_align="left",
            type="password",
            theme="dark",
        )
        qtbot.addWidget(otp)
        assert otp._length == 6
        assert otp._allowed_keys == "^[A-F]*$"
        assert otp._variant == "bordered"
        assert otp._color == "primary"
        assert otp._size == "lg"
        assert otp._radius == "full"
        assert otp.value() == "AB"
        assert otp._description == "Enter code"
        assert otp._text_align == "left"
        assert otp._type == "password"
        assert otp._theme == "dark"

    def test_invalid_values_fall_back(self, qtbot):
        otp = InputOtp(variant="ghost", size="xxl", radius="hex", text_align="top")
        qtbot.addWidget(otp)
        assert otp._variant == "flat"
        assert otp._size == "md"
        assert otp._radius == "md"
        assert otp._text_align == "center"

    def test_min_length_clamped(self, qtbot):
        otp = InputOtp(length=0)
        qtbot.addWidget(otp)
        assert otp._length == 1

    def test_row_size_hint(self, qtbot):
        otp = InputOtp(length=4)
        qtbot.addWidget(otp)
        # 段行四周 2px 活动段外扩预留 + 4 段 × md 40 + 3 间隔 × 4
        assert otp._row.row_size_hint().width() == 4 + 4 * 40 + 3 * 4
        assert otp._row.row_size_hint().height() == 4 + INPUT_OTP_SIZES["md"]["segment"]


class TestValueEditing:
    """插入 / 过滤 / 删除 / 光标"""

    def test_insert_digit_advances_cursor(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        assert otp._insert_text("5")
        assert otp.value() == "5"
        assert otp._cursor == 1

    def test_allowed_keys_filter(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp._insert_text("a!")
        assert otp.value() == ""
        otp.set_allowed_keys("^[A-F]*$")
        otp._insert_text("ABz9")
        assert otp.value() == "AB"

    def test_insert_truncates_at_length(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp._insert_text("12345678")
        assert otp.value() == "1234"

    def test_insert_at_cursor_middle(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp.set_value("12")
        otp._insert_text("9")
        assert otp.value() == "129"

    def test_backspace(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp.set_value("12")
        otp._backspace()
        assert otp.value() == "1"
        assert otp._cursor == 1
        otp._backspace()
        assert otp.value() == ""
        otp._backspace()  # 空值再退格不崩溃，光标钳 0
        assert otp._cursor == 0

    def test_delete_at_cursor(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp.set_value("12")
        otp._set_cursor(0)
        otp._delete_at_cursor()
        assert otp.value() == "2"

    def test_cursor_moves_and_clamps(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp.set_value("123")
        otp._move_cursor(-1)
        assert otp._cursor == 2
        otp._move_cursor(-99)
        assert otp._cursor == 0
        otp._move_cursor(99)
        assert otp._cursor == 4  # 上限 = length（末段后）

    def test_paste_filters_and_truncates(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        assert otp._insert_text("9x8y7z6")
        assert otp.value() == "9876"

    def test_read_only_blocks_edit(self, qtbot):
        otp = InputOtp(is_read_only=True)
        qtbot.addWidget(otp)
        assert not otp._insert_text("5")
        assert otp.value() == ""

    def test_disabled_blocks_edit(self, qtbot):
        otp = InputOtp(is_disabled=True)
        qtbot.addWidget(otp)
        assert not otp._insert_text("5")
        assert otp.value() == ""

    def test_set_value_keeps_allowed_only(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp.set_value("1a2b3")
        assert otp.value() == "123"
        assert otp._cursor == 3


class TestSignals:
    """value_changed / completed"""

    def test_value_changed_fires(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        changes = []
        otp.value_changed.connect(changes.append)
        otp._insert_text("1")
        assert changes == ["1"]

    def test_completed_fires_when_full(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        done = []
        otp.completed.connect(done.append)
        otp.set_value("123")
        assert done == []
        otp.set_value("1234")
        assert done == ["1234"]


class TestLengthAndHelper:
    """set_length 与 helper 行"""

    def test_set_length_truncates_value(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp.set_value("1234")
        otp.set_length(2)
        assert otp._length == 2
        assert otp.value() == "12"
        assert otp._cursor <= 2

    def test_description_shown(self, qtbot):
        otp = InputOtp(description="Enter code")
        qtbot.addWidget(otp)
        assert otp._helper_label.text() == "Enter code"

    def test_error_overrides_description(self, qtbot):
        otp = InputOtp(description="Enter code", error_message="Wrong code")
        qtbot.addWidget(otp)
        otp.set_invalid(True)
        assert otp._helper_label.text() == "Wrong code"

    def test_no_helper_without_texts(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp.set_invalid(True)
        assert otp._helper_label.text() == ""


class TestVisualTokens:
    """variant × color × invalid 的段配色 token"""

    def test_flat_default_tokens(self, qtbot):
        otp = InputOtp(variant="flat", color="default", theme="light")
        qtbot.addWidget(otp)
        s = otp._segment_styles()
        assert s["bg"] == "#f4f4f5"
        assert s["border"] == "none"
        assert s["active_bg"] is not None

    def test_bordered_primary_tokens(self, qtbot):
        otp = InputOtp(variant="bordered", color="primary", theme="light")
        qtbot.addWidget(otp)
        s = otp._segment_styles()
        assert s["bg"] == "#ffffff"
        assert s["border"] == "#99c7fb"
        assert s["border_w"] == 2
        assert s["text"] == "#006FEE"

    def test_invalid_flat_uses_danger(self, qtbot):
        otp = InputOtp(variant="flat", color="primary", theme="light", is_invalid=True)
        qtbot.addWidget(otp)
        s = otp._segment_styles()
        assert s["bg"] == "#fee7ef"  # danger-50
        assert s["text"] == "#f31260"
        assert s["caret_color"] == "#f31260"

    def test_invalid_faded_keeps_variant_bg(self, qtbot):
        otp = InputOtp(variant="faded", color="primary", theme="light", is_invalid=True)
        qtbot.addWidget(otp)
        s = otp._segment_styles()
        assert s["bg"] == "#cce3fd"  # 原 faded 底色保留
        assert s["text"] == "#f31260"

    def test_size_tokens(self, qtbot):
        for size, side in (("sm", 32), ("md", 40), ("lg", 48)):
            otp = InputOtp(size=size)
            qtbot.addWidget(otp)
            assert otp._size_token()["segment"] == side

    def test_setters_update_state(self, qtbot):
        otp = InputOtp()
        qtbot.addWidget(otp)
        otp.set_variant("underlined")
        otp.set_radius("full")
        otp.set_text_align("left")
        otp.set_type("password")
        otp.set_read_only(True)
        otp.set_disabled(True)
        otp.set_disable_animation(True)
        assert otp._variant == "underlined"
        assert otp._radius == "full"
        assert otp._text_align == "left"
        assert otp._type == "password"
        assert otp._is_read_only is True
        assert otp._is_disabled is True
