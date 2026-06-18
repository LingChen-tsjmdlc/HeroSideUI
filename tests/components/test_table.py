"""Table 组件测试。"""

import pytest

from hero_side_ui import Table
from hero_side_ui.components.table._palette import (
    resolve_radius_px,
    selected_before_bg,
    selected_text,
)
from hero_side_ui.components.table._cell import _corner_radii


COLUMNS = [
    {"key": "name", "label": "NAME"},
    {"key": "role", "label": "ROLE"},
    {"key": "status", "label": "STATUS"},
]

ROWS = [
    {"key": "1", "name": "Tony", "role": "CEO", "status": "Active"},
    {"key": "2", "name": "Zoey", "role": "Lead", "status": "Paused"},
    {"key": "3", "name": "Jane", "role": "Dev", "status": "Active"},
]


def _make(qtbot, **kwargs) -> Table:
    t = Table(**kwargs)
    qtbot.addWidget(t)
    t.set_columns(COLUMNS)
    t.set_rows(ROWS)
    return t


# ============================================================
# 纯函数 palette（不依赖 qtbot）
# ============================================================
class TestTablePalette:
    def test_radius_none_zero(self):
        assert resolve_radius_px("none", 40) == 0

    def test_radius_lg(self):
        assert resolve_radius_px("lg", 40) == 14

    def test_radius_full_half_height(self):
        assert resolve_radius_px("full", 40) == 20

    def test_selected_before_default_has_alpha(self):
        c = selected_before_bg("default", "light")
        assert c.alpha() < 255  # 半透明行条

    def test_selected_text_primary(self):
        c = selected_text("primary", "light")
        assert c.alpha() == 255


# ============================================================
# 行条圆角拼接
# ============================================================
class TestTableCornerRadii:
    def test_single_each_row_is_pill(self):
        # 单选：每行独立药丸，首列左圆、尾列右圆，与行位置无关
        tl, tr, br, bl = _corner_radii(
            is_multi=False, is_first_row=False, is_last_row=False,
            is_first_col=True, is_last_col=False, r=10,
        )
        assert (tl, bl) == (10, 10) and (tr, br) == (0, 0)

    def test_multi_middle_row_square(self):
        # 多选中间行：四角全直角，连成整块
        tl, tr, br, bl = _corner_radii(
            is_multi=True, is_first_row=False, is_last_row=False,
            is_first_col=True, is_last_col=True, r=10,
        )
        assert (tl, tr, br, bl) == (0, 0, 0, 0)

    def test_multi_first_row_top_rounded(self):
        # 多选首行首列：仅左上圆
        tl, tr, br, bl = _corner_radii(
            is_multi=True, is_first_row=True, is_last_row=False,
            is_first_col=True, is_last_col=False, r=10,
        )
        assert tl == 10 and bl == 0

    def test_multi_last_row_bottom_rounded(self):
        # 多选尾行尾列：仅右下圆
        tl, tr, br, bl = _corner_radii(
            is_multi=True, is_first_row=False, is_last_row=True,
            is_first_col=False, is_last_col=True, r=10,
        )
        assert br == 10 and tr == 0


# ============================================================
# 初始化与非法值 fallback
# ============================================================
class TestTableInit:
    def test_defaults(self, qtbot):
        t = Table()
        qtbot.addWidget(t)
        assert t._color == "default"
        assert t._size == "md"
        assert t._radius == "lg"
        assert t._shadow == "sm"
        assert t._selection_mode == "none"

    def test_invalid_fallback(self, qtbot):
        t = Table(color="xxx", size="xxx", radius="xxx", shadow="xxx",
                  selection_mode="xxx")
        qtbot.addWidget(t)
        assert t._color == "default"
        assert t._size == "md"
        assert t._radius == "lg"
        assert t._shadow == "sm"
        assert t._selection_mode == "none"


# ============================================================
# 样式矩阵
# ============================================================
class TestTableStyleMatrix:
    @pytest.mark.parametrize("color", ["default", "primary", "secondary",
                                       "success", "warning", "danger"])
    @pytest.mark.parametrize("size", ["sm", "md", "lg"])
    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_matrix_propagates(self, qtbot, color, size, theme):
        t = _make(qtbot, color=color, size=size, theme=theme)
        cell = t._cells["1"]["name"]
        assert cell._color == color
        assert cell._size == size
        assert cell._theme == theme


# ============================================================
# 装配 API
# ============================================================
class TestTableAssembly:
    def test_set_columns(self, qtbot):
        t = Table()
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        assert len(t.columns()) == 3
        assert set(t._headers.keys()) == {"name", "role", "status"}

    def test_add_row(self, qtbot):
        t = Table()
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        t.add_row("1", {"name": "A", "role": "B", "status": "C"})
        assert t.rows() == ["1"]
        assert t._cells["1"]["name"].content() is not None

    def test_add_row_list_form(self, qtbot):
        t = Table()
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        t.add_row("1", ["A", "B", "C"])
        assert t._row_data["1"]["name"] == "A"
        assert t._row_data["1"]["status"] == "C"

    def test_set_rows(self, qtbot):
        t = _make(qtbot)
        assert t.rows() == ["1", "2", "3"]

    def test_clear(self, qtbot):
        t = _make(qtbot)
        t.clear()
        assert t.rows() == []
        assert t.selected_keys() == set()

    def test_render_cell(self, qtbot):
        t = Table()
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        called = {}

        def rc(rk, ck, val):
            called[(rk, ck)] = val
            return f"{val}!"

        t.set_render_cell(rc)
        t.set_rows(ROWS)
        assert ("1", "name") in called


# ============================================================
# 选中
# ============================================================
class TestTableSelection:
    def test_single_select(self, qtbot):
        t = _make(qtbot, selection_mode="single")
        t._on_row_clicked("2")
        assert t.selected_keys() == {"2"}
        t._on_row_clicked("3")
        assert t.selected_keys() == {"3"}

    def test_multiple_select(self, qtbot):
        t = _make(qtbot, selection_mode="multiple")
        t._on_row_clicked("1")
        t._on_row_clicked("3")
        assert t.selected_keys() == {"1", "3"}
        t._on_row_clicked("1")
        assert t.selected_keys() == {"3"}

    def test_none_mode_no_select(self, qtbot):
        t = _make(qtbot, selection_mode="none")
        t._on_row_clicked("1")
        assert t.selected_keys() == set()

    def test_disallow_empty(self, qtbot):
        t = _make(qtbot, selection_mode="multiple", disallow_empty_selection=True)
        t.set_selected_keys({"1"})
        t._on_row_clicked("1")  # 试图取消唯一选中项
        assert t.selected_keys() == {"1"}

    def test_select_all(self, qtbot):
        t = _make(qtbot, selection_mode="multiple")
        t._toggle_select_all()
        assert t.selected_keys() == {"1", "2", "3"}
        t._toggle_select_all()
        assert t.selected_keys() == set()

    def test_select_all_state(self, qtbot):
        t = _make(qtbot, selection_mode="multiple")
        assert t._select_all_state() == "none"
        t.set_selected_keys({"1"})
        assert t._select_all_state() == "partial"
        t.set_selected_keys({"1", "2", "3"})
        assert t._select_all_state() == "all"

    def test_selection_changed_signal(self, qtbot):
        t = _make(qtbot, selection_mode="single")
        with qtbot.waitSignal(t.selection_changed, timeout=200) as blocker:
            t._on_row_clicked("2")
        assert blocker.args[0] == {"2"}

    def test_set_selected_keys_single_truncates(self, qtbot):
        t = _make(qtbot, selection_mode="single")
        t.set_selected_keys({"1", "2"})
        assert len(t.selected_keys()) == 1


# ============================================================
# 禁用
# ============================================================
class TestTableDisabled:
    def test_disabled_not_selectable(self, qtbot):
        t = _make(qtbot, selection_mode="single")
        t.set_disabled_keys({"2"})
        t._on_row_clicked("2")
        assert t.selected_keys() == set()

    def test_select_all_skips_disabled(self, qtbot):
        t = _make(qtbot, selection_mode="multiple")
        t.set_disabled_keys({"2"})
        t._toggle_select_all()
        assert "2" not in t.selected_keys()
        assert t.selected_keys() == {"1", "3"}

    def test_inline_and_user_disabled_independent(self, qtbot):
        # 行内联 _disabled 与用户 set_disabled_keys 互不污染
        t = Table(selection_mode="multiple")
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        t.set_rows([
            {"key": "1", "name": "A", "role": "x", "status": "s", "_disabled": True},
            {"key": "2", "name": "B", "role": "y", "status": "s"},
        ])
        assert t.disabled_keys() == {"1"}
        t.set_disabled_keys({"2"})
        # 用户禁用 2，内联禁用 1，应并集
        assert t.disabled_keys() == {"1", "2"}

    def test_disabled_not_leaking_after_set_rows(self, qtbot):
        # 换数据后旧的内联禁用不应残留
        t = Table(selection_mode="multiple")
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        t.set_rows([{"key": "1", "name": "A", "role": "x", "status": "s", "_disabled": True}])
        assert t.disabled_keys() == {"1"}
        t.set_rows([{"key": "9", "name": "Z", "role": "x", "status": "s"}])
        assert t.disabled_keys() == set()

    def test_set_rows_drops_stale_selection(self, qtbot):
        # 换数据后选中集合只保留仍存在的行
        t = _make(qtbot, selection_mode="multiple")
        t.set_selected_keys({"1", "2"})
        t.set_rows([{"key": "2", "name": "B", "role": "y", "status": "s"}])
        assert t.selected_keys() == {"2"}


# ============================================================
# 选择模式切换 / 信号
# ============================================================
class TestTableSelectionModeSwitch:
    def test_switch_to_none_emits_and_clears(self, qtbot):
        t = _make(qtbot, selection_mode="multiple")
        t.set_selected_keys({"1", "2"})
        with qtbot.waitSignal(t.selection_changed, timeout=200) as blocker:
            t.set_selection_mode("none")
        assert blocker.args[0] == set()
        assert t.selected_keys() == set()

    def test_switch_multiple_to_single_truncates(self, qtbot):
        t = _make(qtbot, selection_mode="multiple")
        t.set_selected_keys({"1", "2", "3"})
        t.set_selection_mode("single")
        assert len(t.selected_keys()) == 1

    def test_switch_same_mode_noop(self, qtbot):
        t = _make(qtbot, selection_mode="single")
        # 切到相同模式不应触发重建/异常
        t.set_selection_mode("single")
        assert t.selection_mode() == "single"


# ============================================================
# 排序
# ============================================================
class TestTableSorting:
    def test_sort_clicked_cycles_three_states(self, qtbot):
        t = Table()
        qtbot.addWidget(t)
        t.set_columns([{"key": "name", "label": "N", "allows_sorting": True}])
        t.set_rows(ROWS)
        t._on_header_sort_clicked("name")
        assert t.sort_descriptor() == {"column": "name", "direction": "ascending"}
        t._on_header_sort_clicked("name")
        assert t.sort_descriptor()["direction"] == "descending"
        t._on_header_sort_clicked("name")
        assert t.sort_descriptor() == {"column": None, "direction": None}

    def test_sort_changed_signal(self, qtbot):
        t = Table()
        qtbot.addWidget(t)
        t.set_columns([{"key": "name", "label": "N", "allows_sorting": True}])
        t.set_rows(ROWS)
        with qtbot.waitSignal(t.sort_changed, timeout=200) as blocker:
            t._on_header_sort_clicked("name")
        assert blocker.args == ["name", "ascending"]

    def test_switch_column_resets_ascending(self, qtbot):
        t = Table()
        qtbot.addWidget(t)
        t.set_columns([
            {"key": "name", "label": "N", "allows_sorting": True},
            {"key": "role", "label": "R", "allows_sorting": True},
        ])
        t.set_rows(ROWS)
        t._on_header_sort_clicked("name")
        t._on_header_sort_clicked("name")
        t._on_header_sort_clicked("role")
        assert t.sort_descriptor() == {"column": "role", "direction": "ascending"}


# ============================================================
# 空状态 + setter + 主题传播
# ============================================================
class TestTableSettersAndState:
    def test_empty_state(self, qtbot):
        t = Table(empty_content="Nothing")
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        t.show()
        assert t._empty_widget.isVisible()

    def test_set_color_propagates(self, qtbot):
        t = _make(qtbot)
        t.set_color("danger")
        assert t._cells["1"]["name"]._color == "danger"

    def test_set_is_striped(self, qtbot):
        t = _make(qtbot)
        t.set_is_striped(True)
        assert t._cells["1"]["name"]._is_striped is True

    def test_full_radius_card_stays_lg(self, qtbot):
        # full 仅作用行条/表头；外壳 Card 退回 lg
        t = _make(qtbot, radius="full")
        assert t._radius == "full"
        assert t._card_radius() == "lg"
        assert t._cells["1"]["name"]._radius == "full"

    def test_set_theme_propagates(self, qtbot):
        t = _make(qtbot, theme="light")
        t.set_theme("dark")
        assert t._theme == "dark"
        assert t._cells["1"]["name"]._theme == "dark"

    def test_set_selection_mode_rebuilds(self, qtbot):
        t = _make(qtbot, selection_mode="none")
        t.set_selection_mode("multiple")
        assert t._select_all_cb is not None
        assert len(t._row_checkboxes) == 3


# ============================================================
# placement / 滚动 / sticky 表头
# ============================================================
class TestTableLayout:
    def test_outside_placement(self, qtbot):
        from PySide6.QtWidgets import QLabel

        t = Table(top_content_placement="outside", bottom_content_placement="outside")
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        top, bot = QLabel("top"), QLabel("bot")
        t.set_top_content(top)
        t.set_bottom_content(bot)
        # outside 内容直接挂在 outer layout（Table 自身），不在 Card body 内
        assert t._outer.indexOf(top) >= 0
        assert t._outer.indexOf(bot) >= 0

    def test_max_height_creates_scroll(self, qtbot):
        t = Table(max_height=300)
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        assert t._scroll is not None
        assert t._scroll.maximumHeight() == 300

    def test_no_scroll_by_default(self, qtbot):
        t = _make(qtbot)
        assert t._scroll is None

    def test_invalid_placement_fallback(self, qtbot):
        t = Table(top_content_placement="xxx")
        qtbot.addWidget(t)
        assert t._top_placement == "inside"


# ============================================================
# 行复用 + 虚拟化
# ============================================================
class TestTableRowReuse:
    def test_reuse_cells_across_set_rows(self, qtbot):
        # 同结构换数据，cell 对象应被复用（id 不变），内容已更新
        t = _make(qtbot)
        cell_before = t._cells["1"]["name"]
        t.set_rows([
            {"key": "1", "name": "AAA", "role": "x", "status": "s"},
            {"key": "2", "name": "B", "role": "y", "status": "s"},
            {"key": "3", "name": "C", "role": "z", "status": "s"},
        ])
        cell_after = t._cells["1"]["name"]
        assert cell_before is cell_after  # 行槽被复用，未销毁重建

    def test_fewer_rows_hides_extra_slots(self, qtbot):
        t = _make(qtbot)
        t.set_rows([{"key": "9", "name": "Z", "role": "x", "status": "s"}])
        assert set(t._cells.keys()) == {"9"}

    def test_structure_change_rebuilds_pool(self, qtbot):
        # 列变化触发引擎 reset，cell 集合重建
        t = _make(qtbot)
        t.set_columns([{"key": "name", "label": "N"}])
        assert set(c for c in t._cells["1"].keys()) == {"name"}


class TestTableVirtualized:
    def test_virtual_auto_scroll(self, qtbot):
        t = Table(is_virtualized=True, selection_mode="multiple")
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        # 虚拟化默认给兜底高度
        assert t._scroll is not None
        assert t._max_height is not None

    def test_virtual_renders_subset(self, qtbot):
        t = Table(is_virtualized=True, max_height=200)
        qtbot.addWidget(t)
        t.set_columns(COLUMNS)
        big = [{"key": str(i), "name": f"U{i}", "role": "r", "status": "s"}
               for i in range(500)]
        t.set_rows(big)
        t.show()
        # 已渲染行数应远小于总行数（只覆盖可视区 + 缓冲）
        assert 0 < len(t._cells) < 500

    def test_virtual_row_height_positive(self, qtbot):
        t = Table(is_virtualized=True)
        qtbot.addWidget(t)
        assert t._virtual_row_height() > 0
