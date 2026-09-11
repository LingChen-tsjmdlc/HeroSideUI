"""Breadcrumbs 与 Spacer 组件测试"""

from __future__ import annotations

from hero_side_ui import BreadcrumbItem, Breadcrumbs, Spacer
from hero_side_ui.components.spacer.spacer import get_margin


class TestBreadcrumbsInit:
    """构造与默认值"""

    def test_default_values(self, qtbot):
        bc = Breadcrumbs()
        qtbot.addWidget(bc)
        assert bc._variant == "light"
        assert bc._color == "foreground"
        assert bc._size == "md"
        assert bc._radius == "sm"
        assert bc._underline == "hover"
        assert bc._max_items == 8
        assert bc._items_before == 1
        assert bc._items_after == 2
        assert bc._hide_separator is False
        assert bc._is_disabled is False

    def test_invalid_fall_back(self, qtbot):
        bc = Breadcrumbs(variant="ghost", color="pink", size="xxl",
                         radius="hex", underline="sometimes")
        qtbot.addWidget(bc)
        assert bc._variant == "light"
        assert bc._color == "foreground"
        assert bc._size == "md"
        assert bc._radius == "sm"
        assert bc._underline == "hover"

    def test_items_rendered_with_separators(self, qtbot):
        bc = Breadcrumbs(items=[
            BreadcrumbItem("Home"), BreadcrumbItem("Music"), BreadcrumbItem("Files"),
        ])
        qtbot.addWidget(bc)
        bc.resize(bc.sizeHint())
        bc.show()
        # 3 项 + 2 分隔符
        assert bc._list_lay.count() == 5

    def test_is_current_auto_on_last(self, qtbot):
        bc = Breadcrumbs(items=[BreadcrumbItem("A"), BreadcrumbItem("B")])
        qtbot.addWidget(bc)
        assert not bc._items[0].is_current
        assert bc._items[1].is_current

    def test_explicit_current_wins(self, qtbot):
        bc = Breadcrumbs(items=[
            BreadcrumbItem("A", is_current=True), BreadcrumbItem("B"),
        ])
        qtbot.addWidget(bc)
        # 官方 isCurrent = isLast || child.props.isCurrent——非 last 也可 current
        assert bc._items[0].is_current


class TestBreadcrumbsCollapse:
    """maxItems 折叠"""

    def _collapsed(self, qtbot, count=5, max_items=3, before=1, after=2):
        bc = Breadcrumbs(
            items=[BreadcrumbItem(f"L{i}", key=f"k{i}") for i in range(count)],
            max_items=max_items, items_before_collapse=before,
            items_after_collapse=after,
        )
        qtbot.addWidget(bc)
        bc.resize(bc.sizeHint())
        bc.show()
        return bc

    def test_collapse_renders_ellipsis(self, qtbot):
        bc = self._collapsed(qtbot)
        # 1 + ellipsis + 2 = 4 widget + 3 separator
        assert bc._list_lay.count() == 7

    def test_no_collapse_below_max(self, qtbot):
        bc = Breadcrumbs(items=[BreadcrumbItem(f"L{i}") for i in range(3)],
                         max_items=8)
        qtbot.addWidget(bc)
        bc.resize(bc.sizeHint())
        bc.show()
        assert bc._list_lay.count() == 3 + 2

    def test_invalid_combination_no_collapse(self, qtbot):
        # before+after >= count 时官方 warn 并跳过折叠
        bc = Breadcrumbs(items=[BreadcrumbItem(f"L{i}") for i in range(4)],
                         max_items=3, items_before_collapse=2,
                         items_after_collapse=2)
        qtbot.addWidget(bc)
        bc.resize(bc.sizeHint())
        bc.show()
        assert bc._list_lay.count() == 4 + 3

    def test_ellipsis_clicks_first_collapsed(self, qtbot):
        bc = self._collapsed(qtbot)
        fired = []
        bc.action_triggered.connect(fired.append)
        # 折叠区第一项 = 索引 before=1 → k1
        bc._on_item_pressed(bc._items[1])
        assert fired == ["k1"]


class TestBreadcrumbsSignals:
    """onAction / item_pressed"""

    def test_action_triggered(self, qtbot):
        bc = Breadcrumbs(items=[BreadcrumbItem("A", key="a"), BreadcrumbItem("B", key="b")])
        qtbot.addWidget(bc)
        fired = []
        bc.action_triggered.connect(fired.append)
        bc._on_item_pressed(bc._items[0])
        assert fired == ["a"]

    def test_item_pressed_signal(self, qtbot):
        bc = Breadcrumbs(items=[BreadcrumbItem("A", key="a")])
        qtbot.addWidget(bc)
        got = []
        bc.item_pressed.connect(got.append)
        bc._on_item_pressed(bc._items[0])
        assert got and got[0].label == "A"


class TestBreadcrumbsDisabled:
    """isDisabled 全局：非 last 禁用，last 保持可用"""

    def test_global_disabled(self, qtbot):
        bc = Breadcrumbs(items=[BreadcrumbItem("A"), BreadcrumbItem("B")],
                         is_disabled=True)
        qtbot.addWidget(bc)
        assert bc._items[0].is_disabled
        assert not bc._items[1].is_disabled

    def test_set_disabled(self, qtbot):
        bc = Breadcrumbs(items=[BreadcrumbItem("A"), BreadcrumbItem("B")])
        qtbot.addWidget(bc)
        bc.set_disabled(True)
        assert bc._items[0].is_disabled


class TestBreadcrumbsVariants:
    """variant 容器样式"""

    def test_solid_has_bg(self, qtbot):
        bc = Breadcrumbs(items=[BreadcrumbItem("A")], variant="solid", theme="light")
        qtbot.addWidget(bc)
        from hero_side_ui.components.breadcrumbs._styling import build_list_styles
        assert build_list_styles("solid", "light")["bg"] == "#f4f4f5"

    def test_bordered_has_border(self, qtbot):
        from hero_side_ui.components.breadcrumbs._styling import build_list_styles
        s = build_list_styles("bordered", "light")
        assert s["border"] == "#e4e4e7"
        assert s["border_w"] == 2

    def test_light_empty(self, qtbot):
        from hero_side_ui.components.breadcrumbs._styling import build_list_styles
        assert build_list_styles("light", "light")["bg"] == "none"


class TestSpacer:
    """Spacer 间距填充器"""

    def test_spacing_scale(self, qtbot):
        assert get_margin(1) == 4
        assert get_margin(2) == 8
        assert get_margin(0.5) == 2
        assert get_margin("px") == 1
        assert get_margin(8) == 32
        assert get_margin(0) == 0

    def test_fixed_size_is_margin(self, qtbot):
        sp = Spacer(x=4, y=2)
        qtbot.addWidget(sp)
        # Qt 布局不认 contentsMargins——空白由本体尺寸撑出
        assert sp.maximumSize().width() == 16
        assert sp.maximumSize().height() == 8

    def test_setters(self, qtbot):
        sp = Spacer()
        qtbot.addWidget(sp)
        sp.set_x(3)
        sp.set_y(6)
        assert sp.x_space() == 3
        assert sp.y_space() == 6
        assert sp.maximumSize().width() == 12
        assert sp.maximumSize().height() == 24

    def test_default_one(self, qtbot):
        sp = Spacer()
        qtbot.addWidget(sp)
        assert sp.maximumSize().width() == 4
        assert sp.maximumSize().height() == 4
