"""ARCH-04：全局字体变化后，依赖字体的组件必须跟随刷新。"""

import pytest
from PySide6.QtWidgets import QApplication

from hero_side_ui import (
    Breadcrumbs,
    Button,
    Calendar,
    Checkbox,
    DateInput,
    Divider,
    Input,
    InputOtp,
    Link,
    NumberInput,
    Pagination,
    Radio,
    Slider,
    Switch,
    TabItem,
    Textarea,
    TimeInput,
)
from hero_side_ui.components.breadcrumbs import BreadcrumbItem
from hero_side_ui.core import FontProvider

CHANGED = "Arial"


@pytest.fixture(autouse=True)
def restore_font():
    yield
    FontProvider.instance().set_family("")


def _crumb_font(w):
    return w._crumbs[0]._font if hasattr(w, "_crumbs") and w._crumbs else None


# 名称 -> (构造函数, 取出被缓存字体的函数)
CASES = {
    "button": (lambda: Button("ok"), lambda w: w.font()),
    "checkbox": (lambda: Checkbox("c"), lambda w: w.font()),
    "radio": (lambda: Radio("r"), lambda w: w.font()),
    "switch": (lambda: Switch("s"), lambda w: w.font()),
    "tab_item": (lambda: TabItem("tab"), lambda w: w.font()),
    "input": (lambda: Input(label="x", placeholder="p"), lambda w: w.line_edit.font()),
    "number_input": (lambda: NumberInput(label="x"), lambda w: w.line_edit.font()),
    "textarea": (lambda: Textarea(label="x"), lambda w: w.text_edit.font()),
    "date_input": (lambda: DateInput(label="x"), lambda w: w._segment_widgets[0].font()),
    "time_input": (lambda: TimeInput(label="x"), lambda w: w._segment_widgets[0].font()),
    "input_otp": (lambda: InputOtp(4), lambda w: w._font),
    "divider": (lambda: Divider(text="or"), lambda w: w._build_font()),
    "breadcrumbs": (
        lambda: Breadcrumbs(items=[BreadcrumbItem("Home"), BreadcrumbItem("Doc")]),
        _crumb_font,
    ),
}


@pytest.mark.parametrize("name", CASES)
def test_font_family_change_reaches_the_component(qtbot, name):
    make, font_of = CASES[name]
    w = make()
    qtbot.addWidget(w)
    assert FontProvider.instance().is_registered(w)
    before = font_of(w).family()
    assert before != CHANGED
    FontProvider.instance().set_family(CHANGED)
    assert font_of(w).family() == CHANGED


@pytest.mark.parametrize("name", ["pagination", "slider", "calendar"])
def test_paint_time_components_are_registered_and_repaint(qtbot, name):
    w = {"pagination": lambda: Pagination(total=5), "slider": Slider, "calendar": Calendar}[name]()
    qtbot.addWidget(w)
    assert FontProvider.instance().is_registered(w)
    FontProvider.instance().set_family(CHANGED)  # 不应抛异常


def test_date_segment_keeps_its_token_size_after_a_font_change(qtbot):
    w = DateInput(label="x")
    qtbot.addWidget(w)
    seg = w._segment_widgets[0]
    size = seg.font().pixelSize()
    FontProvider.instance().set_family(CHANGED)
    assert seg.font().pixelSize() == size


def test_input_floating_label_keeps_its_size_after_a_font_change(qtbot):
    w = Input(label="x")
    qtbot.addWidget(w)
    size = w._inside_label.font().pixelSize()
    FontProvider.instance().set_family(CHANGED)
    assert w._inside_label.font().pixelSize() == size


def test_link_keeps_its_underline_after_a_font_change(qtbot):
    w = Link("l", underline="always")
    qtbot.addWidget(w)
    assert w._text.font().underline()
    FontProvider.instance().set_family(CHANGED)
    assert w._text.font().underline()
    assert w._text.font().family() == CHANGED


def test_button_width_follows_the_new_font(qtbot):
    w = Button("A reasonably long caption")
    qtbot.addWidget(w)
    w.show()
    FontProvider.instance().set_family(CHANGED)
    fresh = Button("A reasonably long caption")
    qtbot.addWidget(fresh)
    assert w.sizeHint().width() == fresh.sizeHint().width()


def test_destroyed_components_do_not_break_the_broadcast(qtbot):
    from shiboken6 import delete

    w = Button("gone")
    delete(w)
    FontProvider.instance().set_family(CHANGED)
    assert QApplication.instance() is not None


def test_code_fonts_are_independent_of_the_global_family(qtbot):
    from hero_side_ui import CodeBlock

    w = CodeBlock("x = 1", language="python")
    qtbot.addWidget(w)
    before = w._code_label.font().family()
    FontProvider.instance().set_family(CHANGED)
    assert w._code_label.font().family() == before
