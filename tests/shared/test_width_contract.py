"""宽度约定：建议宽度只当 sizeHint，用户设宽直接生效；内容型组件不被布局拉宽。

对照官方 HeroUI：输入类是"铺满型"（w-full），Button / Chip / Checkbox 等是"内容型"
（inline-flex / max-w-fit），宽度恰好等于内容，full_width=True 才撑满。
"""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLayout, QSizePolicy, QVBoxLayout, QWidget

from hero_side_ui import (
    Accordion,
    Autocomplete,
    Avatar,
    Badge,
    Button,
    Checkbox,
    Chip,
    CodeEditor,
    DateInput,
    DatePicker,
    DateRangePicker,
    Divider,
    Input,
    InputOtp,
    NumberInput,
    Pagination,
    Radio,
    Select,
    Slider,
    Switch,
    Tabs,
    Textarea,
    TimeInput,
)
from hero_side_ui._shared.fields import InputWrapper, SuggestedWidthMixin, release_width_floor
from hero_side_ui.themes import (
    BUTTON_SIZES,
    DROPDOWN_SIZES,
    INPUT_SIZES,
    TABS_SIZES,
    TEXTAREA_SIZES,
)
from hero_side_ui.themes.width import SUGGESTED_WIDTH
from tests._waits import flush, until

ITEMS = [("a", "Alpha")]


# qtbot.addWidget 只持弱引用：调用方丢掉 _show 的返回值时，宿主窗口会被立刻回收，
# 里面的控件在 C++ 侧一并删除（macOS CI 上表现为 "already deleted"），所以统一强引用到测试结束。
_LIVE_HOSTS: list[QWidget] = []


@pytest.fixture(autouse=True)
def _release_hosts():
    yield
    _LIVE_HOSTS.clear()


def _show(qtbot, widget, layout_cls=QHBoxLayout, stretch=True, size=(900, 300)) -> QWidget:
    """把 widget 放进宿主窗口并显示；stretch 为 True 时尾部加弹簧。"""
    host = QWidget()
    host.resize(*size)
    lay = layout_cls(host)
    lay.addWidget(widget)
    if stretch:
        lay.addStretch(1)
    qtbot.addWidget(host)
    _LIVE_HOSTS.append(host)
    host.show()
    qtbot.waitExposed(host)
    flush(qtbot)
    return host


def _tabs(full_width: bool = False) -> Tabs:
    tabs = Tabs(full_width=full_width)
    tabs.add_tab("Tab A", QLabel("a"))
    tabs.add_tab("Tab B", QLabel("b"))
    return tabs


# ============================================================
# 建议宽度（SuggestedWidthMixin）
# ============================================================
class _Probe(SuggestedWidthMixin, QWidget):
    """只带建议宽度的最小控件。"""


class TestSuggestedWidthMixin:
    def test_suggested_width_is_the_size_hint_of_an_empty_widget(self, qtbot):
        w = _Probe()
        qtbot.addWidget(w)
        w.set_suggested_width(120)
        assert w.suggested_width() == 120
        assert w.sizeHint().width() == 120

    def test_negative_values_become_zero(self, qtbot):
        w = _Probe()
        qtbot.addWidget(w)
        w.set_suggested_width(-5)
        assert w.suggested_width() == 0

    def test_content_wider_than_suggested_wins(self, qtbot):
        w = _Probe()
        qtbot.addWidget(w)
        QHBoxLayout(w).addWidget(QLabel("x" * 80))
        w.set_suggested_width(50)
        assert w.sizeHint().width() > 50

    def test_suggested_width_is_never_a_minimum(self, qtbot):
        w = _Probe()
        qtbot.addWidget(w)
        w.set_suggested_width(300)
        assert w.minimumWidth() == 0
        w.setFixedWidth(40)
        assert w.width() == 40

    def test_release_width_floor_clears_wrapper_minimum(self, qtbot):
        wrapper = QWidget()
        qtbot.addWidget(wrapper)
        QHBoxLayout(wrapper)
        wrapper.setMinimumWidth(260)
        release_width_floor(wrapper)
        assert wrapper.minimumWidth() == 0
        assert wrapper.layout().sizeConstraint() == QLayout.SizeConstraint.SetNoConstraint


# ============================================================
# 输入类：用户设宽直接生效，外框不超出外壳
# ============================================================
INPUT_FACTORIES = {
    "Input": lambda: Input(label="x"),
    "Textarea": lambda: Textarea(label="x"),
    "NumberInput": lambda: NumberInput(label="x"),
    "DateInput": lambda: DateInput(),
    "TimeInput": lambda: TimeInput(),
    "Select": lambda: Select(items=ITEMS, label="x"),
    "Autocomplete": lambda: Autocomplete(items=ITEMS, label="x"),
    "DatePicker": lambda: DatePicker(),
}


@pytest.mark.parametrize("name", list(INPUT_FACTORIES))
class TestInputFamilyWidth:
    @pytest.mark.parametrize("fixed", [40, 80, 150])
    def test_fixed_width_is_honored_and_the_frame_stays_inside(self, qtbot, name, fixed):
        w = INPUT_FACTORIES[name]()
        w.setFixedWidth(fixed)
        _show(qtbot, w)
        assert w.width() == fixed
        for frame in w.findChildren(InputWrapper):
            right = frame.mapTo(w, QPoint(frame.width(), 0)).x()
            assert right <= w.width()

    def test_no_hard_minimum(self, qtbot, name):
        w = INPUT_FACTORIES[name]()
        qtbot.addWidget(w)
        assert w.minimumWidth() == 0
        for frame in w.findChildren(InputWrapper):
            assert frame.minimumWidth() == 0

    def test_restyle_does_not_touch_user_width(self, qtbot, name):
        w = INPUT_FACTORIES[name]()
        w.setFixedWidth(120)
        qtbot.addWidget(w)
        if hasattr(w, "set_color"):
            w.set_color("primary")
        assert w.minimumWidth() == 120
        assert w.maximumWidth() == 120


class TestSuggestedWidthValues:
    def test_one_global_value_taken_from_the_official_max_w_xs(self):
        assert SUGGESTED_WIDTH == 320

    @pytest.mark.parametrize("name", list(INPUT_FACTORIES))
    def test_every_input_class_uses_the_same_suggested_width(self, qtbot, name):
        w = INPUT_FACTORIES[name]()
        qtbot.addWidget(w)
        assert w.sizeHint().width() >= SUGGESTED_WIDTH

    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_size_does_not_change_the_suggested_width(self, qtbot, size):
        ipt = Input(label="x", size=size)
        qtbot.addWidget(ipt)
        assert ipt.suggested_width() == SUGGESTED_WIDTH

    def test_presets_have_no_width_keys_left(self):
        for table in (INPUT_SIZES, TEXTAREA_SIZES):
            assert all(
                "min_width" not in cfg and "default_width" not in cfg for cfg in table.values()
            )

    def test_natural_width_in_a_row_with_a_spring_is_the_suggested_one(self, qtbot):
        w = Input(label="x")
        _show(qtbot, w)
        assert w.width() == SUGGESTED_WIDTH

    def test_autocomplete_inner_input_follows_the_outer_width(self, qtbot):
        # 回归：Autocomplete 设宽曾漏转发，外壳 150 而内部 Input 仍是 260
        w = Autocomplete(items=ITEMS, label="x")
        w.setFixedWidth(150)
        _show(qtbot, w)
        assert w._input.width() == 150


# ============================================================
# full_width 与水平策略
# ============================================================
class TestFullWidth:
    def test_select_defaults_to_full_width(self, qtbot):
        s = Select(items=ITEMS)
        qtbot.addWidget(s)
        assert s.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
        assert s.minimumWidth() == 0

    def test_select_not_full_width_keeps_at_least_160(self, qtbot):
        s = Select(items=ITEMS, full_width=False)
        qtbot.addWidget(s)
        assert s.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Preferred
        assert s.minimumWidth() == 160

    def test_select_set_full_width_toggles(self, qtbot):
        s = Select(items=ITEMS)
        qtbot.addWidget(s)
        s.set_full_width(False)
        assert s.minimumWidth() == 160
        s.set_full_width(True)
        assert s.minimumWidth() == 0
        assert s.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding

    def test_autocomplete_is_always_expanding(self, qtbot):
        a = Autocomplete(items=ITEMS)
        qtbot.addWidget(a)
        assert a.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding

    @pytest.mark.parametrize("factory", [DatePicker, DateRangePicker])
    def test_date_pickers_follow_full_width(self, qtbot, factory):
        on, off = factory(), factory(full_width=False)
        qtbot.addWidget(on)
        qtbot.addWidget(off)
        assert on.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
        assert off.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Preferred

    def test_accordion_defaults_to_full_width(self, qtbot):
        a = Accordion()
        qtbot.addWidget(a)
        assert a.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding

    def test_accordion_not_full_width_follows_content(self, qtbot):
        a = Accordion(full_width=False)
        qtbot.addWidget(a)
        assert a.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Maximum
        a.set_full_width(True)
        assert a.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding


# ============================================================
# 内容型：宽度恰好等于内容，竖排也不被拉宽
# ============================================================
CONTENT_FACTORIES = {
    "Button": lambda: Button("Click"),
    "Chip": lambda: Chip("chip"),
    "Checkbox": lambda: Checkbox("Check me"),
    "Radio": lambda: Radio("r"),
    "Switch": lambda: Switch(),
    "Pagination": lambda: Pagination(total=5),
    "InputOtp": lambda: InputOtp(),
    "Tabs": lambda: _tabs(),
}


@pytest.mark.parametrize("name", list(CONTENT_FACTORIES))
class TestContentTypeWidth:
    def test_not_stretched_in_a_vertical_layout(self, qtbot, name):
        w = CONTENT_FACTORIES[name]()
        _show(qtbot, w, layout_cls=QVBoxLayout)
        assert w.width() == w.sizeHint().width()

    def test_not_stretched_side_by_side(self, qtbot, name):
        a, b = CONTENT_FACTORIES[name](), CONTENT_FACTORIES[name]()
        host = QWidget()
        host.resize(900, 300)
        lay = QHBoxLayout(host)
        lay.addWidget(a)
        lay.addWidget(b)
        qtbot.addWidget(host)
        host.show()
        qtbot.waitExposed(host)
        flush(qtbot)
        assert a.width() == a.sizeHint().width()
        assert b.width() == b.sizeHint().width()

    def test_horizontal_policy_is_maximum(self, qtbot, name):
        w = CONTENT_FACTORIES[name]()
        qtbot.addWidget(w)
        assert w.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Maximum


@pytest.mark.parametrize(
    "name", ["Button", "Chip", "Checkbox", "Radio", "Switch", "Pagination", "InputOtp"]
)
def test_content_type_is_never_squeezed_below_its_content(qtbot, name):
    w = CONTENT_FACTORIES[name]()
    qtbot.addWidget(w)
    assert w.minimumSizeHint().width() == w.sizeHint().width()


class TestFullWidthOptIn:
    def test_button_full_width_stretches(self, qtbot):
        w = Button("Click", full_width=True)
        _show(qtbot, w, layout_cls=QVBoxLayout)
        assert w.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
        assert w.width() > w.sizeHint().width()

    def test_tabs_full_width_stretches(self, qtbot):
        w = _tabs(full_width=True)
        _show(qtbot, w, layout_cls=QVBoxLayout)
        assert w.width() > w.sizeHint().width()

    def test_input_otp_full_width_stretches(self, qtbot):
        w = InputOtp(full_width=True)
        _show(qtbot, w, layout_cls=QVBoxLayout)
        assert w.width() > w.sizeHint().width()

    def test_button_does_not_grow_in_a_vertical_layout_by_default(self, qtbot):
        # 回归：Button 曾是 Minimum（允许长大），竖排会被拉到整行宽
        w = Button("Click")
        _show(qtbot, w, layout_cls=QVBoxLayout)
        assert w.width() == w.sizeHint().width()


class TestBadge:
    def test_badge_wraps_its_content_in_a_vertical_layout(self, qtbot):
        # 回归：Badge 曾被竖排拉到整行宽，里面的头像被居中到中间
        avatar = Avatar(name="AB")
        badge = Badge(avatar, content="5")
        _show(qtbot, badge, layout_cls=QVBoxLayout)
        assert badge.width() < 200
        assert badge.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Maximum


# ============================================================
# Slider：建议长度
# ============================================================
class TestCodeEditorWidth:
    def test_default_width_is_the_global_suggested_width(self, qtbot):
        # 回归：它的 288 是 Qt QPlainTextEdit 的默认值，没有来历
        e = CodeEditor()
        qtbot.addWidget(e)
        assert e.sizeHint().width() == SUGGESTED_WIDTH

    def test_minimum_width_is_a_fixed_120(self, qtbot):
        e = CodeEditor()
        qtbot.addWidget(e)
        assert e.minimumWidth() == 120

    def test_user_width_still_wins(self, qtbot):
        e = CodeEditor()
        e.setFixedWidth(200)
        _show(qtbot, e)
        assert e.width() == 200


class TestDividerWidth:
    """官方 Divider 是 w-full / h-full：不能在布局里塌成 0。"""

    def test_horizontal_line_fills_a_vertical_layout(self, qtbot):
        d = Divider()
        _show(qtbot, d, layout_cls=QVBoxLayout)
        assert d.width() > SUGGESTED_WIDTH

    def test_horizontal_line_is_not_zero_in_a_row_with_a_spring(self, qtbot):
        d = Divider()
        _show(qtbot, d)
        assert d.width() == SUGGESTED_WIDTH

    def test_vertical_line_is_not_zero_in_a_column_with_a_spring(self, qtbot):
        d = Divider(orientation="vertical")
        _show(qtbot, d, layout_cls=QVBoxLayout, size=(900, 600))  # 窗口要比 320 高，否则被压窄
        assert d.height() == SUGGESTED_WIDTH

    def test_line_survives_an_alignment_flag(self, qtbot):
        # 回归：文档里的反例，带对齐标记的布局条目按 sizeHint 给位，线曾经消失
        host = QWidget()
        host.resize(900, 300)
        lay = QVBoxLayout(host)
        d = Divider()
        lay.addWidget(d, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(1)
        qtbot.addWidget(host)
        host.show()
        qtbot.waitExposed(host)
        flush(qtbot)
        assert d.width() == SUGGESTED_WIDTH

    def test_user_width_still_wins(self, qtbot):
        d = Divider()
        d.setFixedWidth(120)
        _show(qtbot, d)
        assert d.width() == 120


class TestSliderSuggestedLength:
    def test_horizontal_slider_has_a_suggested_width(self, qtbot):
        s = Slider()
        qtbot.addWidget(s)
        assert s.sizeHint().width() >= SUGGESTED_WIDTH

    def test_vertical_slider_has_a_suggested_height(self, qtbot):
        s = Slider(orientation="vertical")
        qtbot.addWidget(s)
        assert s.sizeHint().height() >= SUGGESTED_WIDTH

    def test_slider_does_not_collapse_in_a_row_with_a_spring(self, qtbot):
        s = Slider()
        _show(qtbot, s)
        assert s.width() >= SUGGESTED_WIDTH


# ============================================================
# 数字有来历：和官方 HeroUI 对得上的值
# ============================================================
class TestOfficialNumbers:
    @pytest.mark.parametrize("size,total", [("sm", 64), ("md", 80), ("lg", 96)])
    @pytest.mark.parametrize("variant", ["solid", "bordered", "faded", "ghost"])
    def test_button_min_width_is_official_min_w(self, qtbot, size, total, variant):
        # 官方 min-w-16 / 20 / 24 是含留白与边框的总宽
        btn = Button("A", size=size, variant=variant)
        qtbot.addWidget(btn)
        btn.ensurePolished()
        assert btn.sizeHint().width() == total

    def test_button_large_padding_is_official_px_6(self):
        assert BUTTON_SIZES["lg"]["padding_x"] == 24
        assert BUTTON_SIZES["md"]["padding_x"] == 16
        assert BUTTON_SIZES["sm"]["padding_x"] == 12

    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    def test_dropdown_menu_min_width_is_a_single_200(self, size):
        assert DROPDOWN_SIZES[size]["menu_min_width"] == 200

    def test_tabs_have_no_hardcoded_tab_min_width(self):
        assert all("tab_min_width" not in cfg for cfg in TABS_SIZES.values())

    @pytest.mark.parametrize("size,box", [("sm", 16), ("md", 20), ("lg", 24)])
    def test_table_checkbox_column_is_box_plus_padding(self, qtbot, size, box):
        from hero_side_ui import Table
        from hero_side_ui.components.table._hosts import _CheckboxCell
        from hero_side_ui.themes import TABLE_SIZES

        t = Table(selection_mode="multiple", size=size)
        t.set_columns([{"key": "a", "label": "A"}])
        t.add_row("1", ["x"])
        _show(qtbot, t, layout_cls=QVBoxLayout, stretch=False, size=(500, 300))
        widths = {c.width() for c in t.findChildren(_CheckboxCell)}
        assert widths == {box + 2 * TABLE_SIZES[size]["cell_padding_x"]}

    @pytest.mark.parametrize("size,side", [("sm", 8), ("md", 12), ("lg", 16)])
    def test_chip_side_padding_is_official_base_plus_content(self, size, side):
        from hero_side_ui.themes import CHIP_SIZES

        assert CHIP_SIZES[size]["padding_x"] == side

    def test_radio_card_is_capped_at_the_global_width(self, qtbot):
        r = Radio("Option", description="x" * 300, variant="card")
        qtbot.addWidget(r)
        assert r.sizeHint().width() <= SUGGESTED_WIDTH
