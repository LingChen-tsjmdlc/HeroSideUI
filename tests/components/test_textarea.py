"""Textarea 组件测试"""

import pytest
from PySide6.QtCore import Qt

from hero_side_ui import Textarea, Button


VARIANTS = ["flat", "faded", "bordered"]  # textarea 不支持 underlined
COLORS = ["default", "primary", "secondary", "success", "warning", "danger"]
SIZES = ["sm", "md", "lg"]
PLACEMENTS = ["inside", "outside", "outside-top", "outside-left"]


class TestTextareaInit:
    """构造参数测试"""

    def test_default_params(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        assert ta.text() == ""
        assert ta._variant == "flat"
        assert ta._color == "default"
        assert ta._size == "md"
        assert ta._label_placement == "inside"
        assert ta._theme_mode == "auto"
        assert ta._min_rows == 3
        assert ta._max_rows == 8
        assert not ta._disable_autosize
        assert not ta._is_disabled
        assert not ta._is_invalid
        # resizable 默认关闭
        assert ta._resize_mode is None
        # 三槽默认 None
        assert ta._top_right_content is None
        assert ta._center_right_content is None
        assert ta._bottom_right_content is None

    def test_custom_params(self, qtbot):
        ta = Textarea(
            label="Description",
            value="hello\nworld",
            placeholder="type...",
            variant="bordered",
            color="primary",
            size="lg",
            radius="lg",
            label_placement="outside",
            min_rows=2,
            max_rows=10,
            is_required=True,
            is_clearable=True,
            description="desc",
            theme="dark",
            resizable=True,
        )
        qtbot.addWidget(ta)
        assert ta.text() == "hello\nworld"
        assert ta._variant == "bordered"
        assert ta._color == "primary"
        assert ta._size == "lg"
        assert ta._radius == "lg"
        assert ta._label_placement == "outside"
        assert ta._min_rows == 2
        assert ta._max_rows == 10
        assert ta._is_required
        assert ta._is_clearable
        assert ta._theme == "dark"
        assert ta._resize_mode == "vertical"

    def test_underlined_falls_back_to_flat(self, qtbot):
        """传 underlined 应静默降级为 flat"""
        ta = Textarea(variant="underlined")
        qtbot.addWidget(ta)
        assert ta._variant == "flat"

    def test_max_rows_min_rows_clamp(self, qtbot):
        """max_rows < min_rows 时应自动 clamp"""
        ta = Textarea(min_rows=5, max_rows=2)
        qtbot.addWidget(ta)
        assert ta._min_rows == 5
        assert ta._max_rows >= 5

    def test_disabled(self, qtbot):
        ta = Textarea(label="x", is_disabled=True)
        qtbot.addWidget(ta)
        assert ta._is_disabled
        assert not ta.text_edit.isEnabled()

    def test_readonly(self, qtbot):
        ta = Textarea(label="x", is_readonly=True)
        qtbot.addWidget(ta)
        assert ta.text_edit.isReadOnly()


class TestTextareaVariants:
    @pytest.mark.parametrize("variant", VARIANTS)
    def test_all_variants(self, qtbot, variant):
        ta = Textarea(label="L", variant=variant)
        qtbot.addWidget(ta)
        assert ta._variant == variant


class TestTextareaColors:
    @pytest.mark.parametrize("color", COLORS)
    def test_all_colors(self, qtbot, color):
        ta = Textarea(label="L", color=color)
        qtbot.addWidget(ta)
        assert ta._color == color


class TestTextareaSizes:
    @pytest.mark.parametrize("size", SIZES + ["small", "medium", "large"])
    def test_all_sizes(self, qtbot, size):
        ta = Textarea(label="L", size=size)
        qtbot.addWidget(ta)
        assert ta._size == size


class TestTextareaLabelPlacement:
    @pytest.mark.parametrize("placement", PLACEMENTS)
    def test_all_placements(self, qtbot, placement):
        ta = Textarea(label="L", label_placement=placement)
        qtbot.addWidget(ta)
        assert ta._label_placement == placement


class TestTextareaCombinations:
    """关键组合不崩"""

    def test_all_variant_color_size_combos(self, qtbot):
        for v in VARIANTS:
            for c in COLORS:
                for s in SIZES:
                    ta = Textarea(label=f"{v}-{c}", variant=v, color=c, size=s)
                    qtbot.addWidget(ta)
                    assert ta._variant == v and ta._color == c and ta._size == s


class TestTextareaDynamicAPI:
    def test_set_text_clear(self, qtbot):
        ta = Textarea(label="L")
        qtbot.addWidget(ta)
        ta.set_text("abc\ndef")
        assert ta.text() == "abc\ndef"
        ta.clear()
        assert ta.text() == ""

    def test_set_value_alias(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_value("xyz")
        assert ta.text() == "xyz"

    def test_set_variant(self, qtbot):
        ta = Textarea(variant="flat")
        qtbot.addWidget(ta)
        ta.set_variant("bordered")
        assert ta._variant == "bordered"

    def test_set_variant_underlined_downgrades(self, qtbot):
        ta = Textarea(variant="flat")
        qtbot.addWidget(ta)
        ta.set_variant("underlined")
        assert ta._variant == "flat"

    def test_set_color(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_color("danger")
        assert ta._color == "danger"

    def test_set_size(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_size("lg")
        assert ta._size == "lg"

    def test_set_radius(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_radius("full")
        assert ta._radius == "full"

    def test_set_min_rows(self, qtbot):
        ta = Textarea(min_rows=3, max_rows=8)
        qtbot.addWidget(ta)
        ta.set_min_rows(5)
        assert ta._min_rows == 5

    def test_set_max_rows(self, qtbot):
        ta = Textarea(min_rows=3, max_rows=8)
        qtbot.addWidget(ta)
        ta.set_max_rows(12)
        assert ta._max_rows == 12

    def test_set_disable_autosize(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_disable_autosize(True)
        assert ta._disable_autosize

    def test_set_theme(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_theme("dark")
        assert ta._theme == "dark"

    def test_set_is_invalid(self, qtbot):
        ta = Textarea(error_message="err")
        qtbot.addWidget(ta)
        ta.set_is_invalid(True)
        assert ta._is_invalid
        assert not ta._helper_label.isHidden()

    def test_set_is_disabled(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_is_disabled(True)
        assert ta._is_disabled
        assert not ta.text_edit.isEnabled()

    def test_set_is_readonly(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_is_readonly(True)
        assert ta.text_edit.isReadOnly()

    def test_set_label_placement(self, qtbot):
        ta = Textarea(label="x", label_placement="inside")
        qtbot.addWidget(ta)
        ta.set_label_placement("outside-top")
        assert ta._label_placement == "outside-top"

    def test_set_label(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_label("New")
        assert ta._label_text == "New"

    def test_set_description(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_description("desc")
        assert ta._description == "desc"
        assert not ta._helper_label.isHidden()


class TestTextareaSignals:
    def test_text_changed_signal(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        with qtbot.waitSignal(ta.text_changed, timeout=1000) as blocker:
            ta.set_text("abc")
        assert blocker.args == ["abc"]

    def test_cleared_signal(self, qtbot):
        ta = Textarea(is_clearable=True)
        qtbot.addWidget(ta)
        ta.set_text("xxx")
        with qtbot.waitSignal(ta.cleared, timeout=1000):
            ta._clear_btn.click()


class TestTextareaClearable:
    def test_clear_button_hidden_when_empty(self, qtbot):
        ta = Textarea(is_clearable=True)
        qtbot.addWidget(ta)
        assert not ta._clear_btn._visible

    def test_clear_button_visible_when_filled(self, qtbot):
        ta = Textarea(is_clearable=True)
        qtbot.addWidget(ta)
        ta.set_text("hello")
        assert ta._clear_btn._visible

    def test_clear_button_clears_text(self, qtbot):
        ta = Textarea(is_clearable=True)
        qtbot.addWidget(ta)
        ta.set_text("hello")
        ta._clear_btn.click()
        assert ta.text() == ""


class TestTextareaSlots:
    """三个内容槽 (top_right / center_right / bottom_right)

    注意：检查"槽是否激活"用 not isHidden()，而不是 isVisible() ——
    isVisible() 需要 widget 整条父链都 show 了才返回 True，
    而单元测试里我们没有 ta.show()，所以即便槽内部 show 过 isVisible 仍 False。
    isHidden() 则只检查"被显式 hide() 过没"，更符合"槽逻辑是否激活"的语义。
    """

    def test_top_right_string_icon(self, qtbot):
        ta = Textarea(top_right_content="heroicons--x-circle-solid")
        qtbot.addWidget(ta)
        assert ta._top_right_content == "heroicons--x-circle-solid"
        assert not ta._top_right_slot.isHidden()

    def test_top_right_widget(self, qtbot):
        btn = Button("X")
        ta = Textarea(top_right_content=btn)
        qtbot.addWidget(ta)
        assert ta._top_right_content is btn

    def test_center_right_widget(self, qtbot):
        btn = Button("Send")
        ta = Textarea(center_right_content=btn)
        qtbot.addWidget(ta)
        assert ta._center_right_content is btn
        assert not ta._center_right_holder.isHidden()

    def test_bottom_right_widget_with_offset(self, qtbot):
        btn = Button("Send")
        ta = Textarea(bottom_right_content=btn, bottom_right_offset=(12, 14))
        qtbot.addWidget(ta)
        assert ta._bottom_right_offset == (12, 14)
        assert not ta._bottom_right_holder.isHidden()

    def test_set_top_right_content(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        btn = Button("X")
        ta.set_top_right_content(btn)
        assert ta._top_right_content is btn

    def test_set_center_right_content(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        btn = Button("Send")
        ta.set_center_right_content(btn)
        assert ta._center_right_content is btn

    def test_set_bottom_right_content(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        btn = Button("Send")
        ta.set_bottom_right_content(btn)
        assert ta._bottom_right_content is btn

    def test_clear_content_to_none(self, qtbot):
        btn = Button("X")
        ta = Textarea(top_right_content=btn)
        qtbot.addWidget(ta)
        ta.set_top_right_content(None)
        assert ta._top_right_content is None
        # 设回 None 后槽应该 hide
        assert ta._top_right_slot.isHidden()


class TestTextareaResizable:
    """手动 grip 拖动"""

    def test_default_no_grip(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        assert ta._resize_mode is None
        assert ta._resize_grip.isHidden()

    def test_resizable_true(self, qtbot):
        ta = Textarea(resizable=True)
        qtbot.addWidget(ta)
        assert ta._resize_mode == "vertical"

    def test_resizable_horizontal(self, qtbot):
        ta = Textarea(resizable="horizontal")
        qtbot.addWidget(ta)
        assert ta._resize_mode == "horizontal"

    def test_resizable_both(self, qtbot):
        ta = Textarea(resizable="both")
        qtbot.addWidget(ta)
        assert ta._resize_mode == "both"

    def test_set_resizable(self, qtbot):
        ta = Textarea()
        qtbot.addWidget(ta)
        ta.set_resizable(True)
        assert ta._resize_mode == "vertical"
        ta.set_resizable(False)
        assert ta._resize_mode is None

    def test_grip_drag_changes_height(self, qtbot):
        ta = Textarea(resizable=True, min_rows=3, max_rows=8)
        qtbot.addWidget(ta)
        ta.show()
        qtbot.waitExposed(ta)
        h0 = ta._wrapper.height()
        # 模拟向下拖动 50px
        ta._on_grip_drag(0, 50)
        assert ta._manual_height is not None
        assert ta._wrapper.height() >= h0  # 高度增加（或受 min 钳制后保持）

    def test_reset_manual_height(self, qtbot):
        ta = Textarea(resizable=True)
        qtbot.addWidget(ta)
        ta.show()
        qtbot.waitExposed(ta)
        ta._on_grip_drag(0, 50)
        assert ta._manual_height is not None
        ta.reset_manual_height()
        assert ta._manual_height is None

    def test_grip_hidden_when_bottom_right_content(self, qtbot):
        """bottom_right_content 存在时 grip 自动隐藏避免重叠"""
        ta = Textarea(resizable=True, bottom_right_content=Button("Send"))
        qtbot.addWidget(ta)
        ta.show()
        qtbot.waitExposed(ta)
        # _reposition_absolute_holders 会在 show 后调
        assert ta._resize_grip.isHidden()


class TestTextareaAutoResize:
    """auto-resize 行为"""

    def test_initial_height_min_rows(self, qtbot):
        ta = Textarea(min_rows=3, max_rows=8)
        qtbot.addWidget(ta)
        ta.show()
        qtbot.waitExposed(ta)
        # 初始无内容时高度对应 min_rows
        h = ta._wrapper.height()
        assert h > 0

    def test_disable_autosize(self, qtbot):
        ta = Textarea(min_rows=4, max_rows=8, disable_autosize=True)
        qtbot.addWidget(ta)
        ta.show()
        qtbot.waitExposed(ta)
        h_before = ta._wrapper.height()
        # 输入大量内容
        ta.set_text("\n".join(f"line {i}" for i in range(20)))
        h_after = ta._wrapper.height()
        # disable_autosize 时高度不应变
        assert h_before == h_after


class TestTextareaScrollBarColor:
    """滚动条颜色注册（color != default 时跟随语义色，default 时用全局 neutral）"""

    def test_default_color_no_override(self, qtbot):
        ta = Textarea(color="default")
        qtbot.addWidget(ta)
        v_bar = ta.text_edit.verticalScrollBar()
        # default 时不注册，bar 上的属性应为 None
        assert v_bar.property("_hs_scroll_color") is None

    def test_primary_color_registers(self, qtbot):
        ta = Textarea(color="primary")
        qtbot.addWidget(ta)
        v_bar = ta.text_edit.verticalScrollBar()
        assert v_bar.property("_hs_scroll_color") == "primary"

    def test_set_color_updates_scroll(self, qtbot):
        ta = Textarea(color="default")
        qtbot.addWidget(ta)
        ta.set_color("success")
        v_bar = ta.text_edit.verticalScrollBar()
        assert v_bar.property("_hs_scroll_color") == "success"
