"""Table 行渲染引擎：行槽池承载行复用与虚拟化。

非虚拟化翻页原地改写复用行槽；虚拟化只为可视区+缓冲建固定槽，上下
spacer 撑滚动总高，代价是行高统一。宿主需提供 _columns/_grid 等字段。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from ..checkbox import Checkbox
from ._cell import _TableCell


class _RowSlot:
    """一个可复用的数据行：可选 checkbox + 各列 cell。"""

    __slots__ = ("cells", "checkbox", "checkbox_holder", "grid_row", "row_key")

    def __init__(self):
        """创建空行槽，初始化 checkbox 与各列 cell 容器。"""
        self.checkbox: Checkbox | None = None
        self.checkbox_holder: QWidget | None = None
        self.cells: dict[str, _TableCell] = {}
        self.row_key: str | None = None
        self.grid_row: int | None = None


class _RowRenderer:
    """数据行渲染引擎，owner 为 Table。"""

    def __init__(self, owner):
        """绑定 Table 持有者并初始化行槽池。

        Args:
            owner: 提供 _columns、_grid 等字段的 Table 实例。
        """
        self.owner = owner
        self._pool: list[_RowSlot] = []
        self._structure_sig = None  # 列 + 是否多选 的结构签名
        self._has_cb = False  # 当前结构是否含 checkbox 列
        self._col_offset = 0
        # 虚拟化 spacer（懒建）
        self._top_spacer: QWidget | None = None
        self._bottom_spacer: QWidget | None = None
        self._first_visible = 0  # 虚拟化：当前窗口首行在全量数据中的下标

    # ------------------------------------------------------------
    # 结构管理
    # ------------------------------------------------------------
    def _structure_signature(self):
        """返回列定义与多选模式组成的结构签名。"""
        return (
            tuple((c["key"], c["align"]) for c in self.owner._columns),
            self.owner._selection_mode == "multiple",
        )

    def reset(self):
        """彻底销毁所有行槽与 spacer（列定义/选择模式变化时）。"""
        grid = self.owner._grid
        for slot in self._pool:
            for w in self._slot_widgets(slot):
                grid.removeWidget(w)
                w.hide()
                w.deleteLater()
        self._pool.clear()
        for sp in (self._top_spacer, self._bottom_spacer):
            if sp is not None:
                grid.removeWidget(sp)
                sp.hide()
                sp.deleteLater()
        self._top_spacer = None
        self._bottom_spacer = None
        self._structure_sig = None

    @staticmethod
    def _slot_widgets(slot: _RowSlot):
        """返回行槽中所有需要挂到网格的 widget。

        Args:
            slot: 目标行槽。

        Returns:
            各列 cell 与可选 checkbox holder 组成的列表。
        """
        ws = list(slot.cells.values())
        if slot.checkbox_holder is not None:
            ws.append(slot.checkbox_holder)
        return ws

    def _ensure_structure(self):
        """结构签名变化时销毁旧行槽并重建结构标记。"""
        sig = self._structure_signature()
        if sig != self._structure_sig:
            self.reset()
            self._structure_sig = sig
            self._has_cb = self.owner._selection_mode == "multiple"
            self._col_offset = 1 if self._has_cb else 0

    # ------------------------------------------------------------
    # 行槽创建 / 定位
    # ------------------------------------------------------------
    def _create_slot(self, slot_index: int) -> _RowSlot:
        """按槽位下标新建一个行槽并挂入网格。

        Args:
            slot_index: 槽位下标，用于计算网格行号。

        Returns:
            新建并加入池的 _RowSlot。

        Note:
            checkbox 必须带 parent=grid_host，否则无父 widget 会瞬间变顶层窗口。
        """
        owner = self.owner
        grid = owner._grid
        slot = _RowSlot()
        grid_row = slot_index + 2  # +1 留给 header(row0)，+1 留给 top spacer(row1)

        if self._has_cb:
            # 必须带 parent=grid_host：无父 widget 会瞬间变顶层窗口，
            # Windows 上批量创建行槽时闪出一堆原生空白窗口。
            cb = Checkbox(
                color=owner._color, size=owner._size, theme="auto", parent=owner._grid_host
            )
            cb.clicked.connect(lambda *_a, s=slot: owner._on_checkbox_clicked(s.row_key))
            holder = owner._checkbox_holder(
                cb, (lambda s=slot: owner._on_checkbox_clicked(s.row_key))
            )
            slot.checkbox = cb
            slot.checkbox_holder = holder
            grid.addWidget(holder, grid_row, 0)

        for ci, col in enumerate(owner._columns):
            cell = _TableCell(None, align=col["align"], parent=owner._grid_host)
            cell.bind_row(None, owner._on_cell_hover, owner._on_row_clicked)
            slot.cells[col["key"]] = cell
            grid.addWidget(cell, grid_row, ci + self._col_offset)

        slot.grid_row = grid_row
        self._pool.append(slot)
        return slot

    def _ensure_slot_count(self, n: int):
        """池中行槽数补足到至少 n（只增不减，多余的靠 hide 隐藏）。"""
        while len(self._pool) < n:
            self._create_slot(len(self._pool))

    # ------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------
    def render(self):
        """非虚拟化：渲染全部行，复用行槽。"""
        self._ensure_structure()
        self._set_spacers(0, 0)
        keys = self.owner._row_order
        self._ensure_slot_count(len(keys))
        for i, slot in enumerate(self._pool):
            if i < len(keys):
                self._fill_slot(slot, keys[i], abs_index=i, total=len(keys))
                self._show_slot(slot, True)
            else:
                self._show_slot(slot, False)
        self._publish_maps(keys, range(len(keys)))

    def render_window(self, first_visible: int, visible_count: int, total: int):
        """虚拟化：只渲染 [first_visible, first_visible+visible_count) 窗口。"""
        self._ensure_structure()
        self._first_visible = first_visible
        keys = self.owner._row_order
        self._ensure_slot_count(visible_count)
        rendered_indices = []
        for i, slot in enumerate(self._pool):
            abs_index = first_visible + i
            if i < visible_count and abs_index < total:
                self._fill_slot(slot, keys[abs_index], abs_index=abs_index, total=total)
                self._show_slot(slot, True)
                rendered_indices.append(abs_index)
            else:
                self._show_slot(slot, False)
        row_h = self.owner._virtual_row_height()
        top_h = first_visible * row_h
        shown = len(rendered_indices)
        bottom_h = max(0, (total - first_visible - shown)) * row_h
        self._set_spacers(top_h, bottom_h)
        self._publish_maps(keys, rendered_indices)

    def _fill_slot(self, slot: _RowSlot, row_key: str, *, abs_index: int, total: int):
        """把一行数据填入指定行槽并刷新各单元格状态。

        Args:
            slot: 目标行槽。
            row_key: 行 key。
            abs_index: 该行在全量数据中的绝对下标。
            total: 全量数据总行数。
        """
        owner = self.owner
        slot.row_key = row_key
        is_multi = owner._selection_mode == "multiple"
        n_cols = len(owner._columns)
        for ci, col in enumerate(owner._columns):
            cell = slot.cells.get(col["key"])
            if cell is None:
                continue
            cell.rebind_row(row_key)
            cell.update_content(owner._make_cell_content(row_key, col["key"]))
            cell.apply_style(
                color=owner._color,
                size=owner._size,
                theme=owner._theme,
                radius=owner._radius,
                is_striped=owner._is_striped,
                is_compact=owner._is_compact,
                is_multi=is_multi,
                align=col["align"],
                disable_animation=owner._disable_animation,
            )
            cell.set_position(
                is_first_row=(abs_index == 0),
                is_last_row=(abs_index == total - 1),
                is_first_col=(ci == 0),
                is_last_col=(ci == n_cols - 1),
            )
        if slot.checkbox is not None:
            slot.checkbox.set_color(owner._color)
            slot.checkbox.setEnabled(row_key not in owner._disabled_keys)

    def _show_slot(self, slot: _RowSlot, visible: bool):
        """显示或隐藏行槽中的全部 widget。

        Args:
            slot: 目标行槽。
            visible: 是否可见；隐藏时清空 row_key。
        """
        if not visible:
            slot.row_key = None
        for w in self._slot_widgets(slot):
            w.setVisible(visible)

    def _publish_maps(self, keys, rendered_indices):
        """把已渲染行的 cell 与 checkbox 发布到 owner 的映射表。

        Args:
            keys: 当前行 key 序列，本实现不读取。
            rendered_indices: 已渲染行的绝对下标序列，本实现不读取。

        Note:
            映射仅取自仍持有 row_key 的行槽，隐藏槽的 row_key 已被清空。
        """
        owner = self.owner
        cells: dict[str, dict] = {}
        cbs: dict[str, Checkbox] = {}
        for slot in self._pool:
            if slot.row_key is None:
                continue
            cells[slot.row_key] = dict(slot.cells)
            if slot.checkbox is not None:
                cbs[slot.row_key] = slot.checkbox
        owner._cells = cells
        owner._row_checkboxes = cbs

    # ------------------------------------------------------------
    # spacer（仅虚拟化时撑滚动总高）
    # ------------------------------------------------------------
    def _make_spacer(self, grid_row: int) -> QWidget:
        """在指定网格行创建跨列的透明 spacer。

        Args:
            grid_row: 网格行号。

        Returns:
            新建的 spacer QWidget。
        """
        sp = QWidget(self.owner._grid_host)
        sp.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        span = max(1, len(self.owner._columns) + self._col_offset)
        self.owner._grid.addWidget(sp, grid_row, 0, 1, span)
        return sp

    def _set_spacers(self, top_h: int, bottom_h: int):
        """按上下留白高度设置虚拟化 spacer 的尺寸与可见性。

        Args:
            top_h: 顶部留白高度。
            bottom_h: 底部留白高度。

        Note:
            上下高度都为 0 且尚未建 spacer 时直接返回，避免非虚拟化场景产生开销。
        """
        # 非虚拟化（top/bottom 都 0）且从未建 spacer → 不创建，省开销
        if top_h <= 0 and bottom_h <= 0 and self._top_spacer is None:
            return
        if self._top_spacer is None:
            self._top_spacer = self._make_spacer(1)
        if self._bottom_spacer is None:
            self._bottom_spacer = self._make_spacer(2 + len(self._pool))
        self._top_spacer.setFixedHeight(max(0, int(top_h)))
        self._bottom_spacer.setFixedHeight(max(0, int(bottom_h)))
        self._top_spacer.setVisible(top_h > 0)
        self._bottom_spacer.setVisible(bottom_h > 0)
