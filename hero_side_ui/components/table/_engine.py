"""Table 行渲染引擎：行复用 + 虚拟化。

把"数据行"的装配从 Table 主体里抽出来，统一用一个**行槽池（slot pool）**承载，
解决两类性能问题：

行复用（默认，非虚拟化）
    翻页 / 换数据时不再销毁重建所有单元格，而是复用已有的行槽：
    cell 走 ``update_content`` 原地改文本、``rebind_row`` 改归属 key，多退少补。

虚拟化（is_virtualized=True，需配合 max_height 滚动）
    只为"可视区 + 缓冲"创建固定数量的行槽，固定占据 grid 的连续行；
    上下各放一个 spacer 行用 ``setRowMinimumHeight`` 撑出滚动总高。
    滚动时只改两个 spacer 高度 + 重填固定行槽内容，行槽本身不挪位、不增减。
    代价：要求**行高统一**（取 token row_min_height），自定义高行内容会被按统一高度排布。

行槽在 grid 中的布局::

    grid row 0                 : 表头（由 Table 主体管理，不属本引擎）
    grid row 1                 : 顶部 spacer（仅虚拟化用，非虚拟化高度 0）
    grid row 2 .. 2+N-1        : N 个数据行槽（N=可视行数或全部行数）
    grid row 2+N               : 底部 spacer（仅虚拟化用）

宿主 Table 需提供：
    _columns / _selection_mode / _render_cell / _row_order / _row_data /
    _selected_keys / _disabled_keys / _color / _size / _theme / _radius /
    _is_striped / _is_compact / _disable_animation / _grid / _grid_host /
    _on_cell_hover / _on_row_clicked / _on_checkbox_clicked / _checkbox_holder /
    _make_cell_content
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from ..checkbox import Checkbox
from ._cell import _TableCell


class _RowSlot:
    """一个可复用的数据行：可选 checkbox + 各列 cell。"""

    __slots__ = ("checkbox", "checkbox_holder", "cells", "row_key", "grid_row")

    def __init__(self):
        self.checkbox: Optional[Checkbox] = None
        self.checkbox_holder: Optional[QWidget] = None
        self.cells: dict[str, _TableCell] = {}
        self.row_key: Optional[str] = None
        self.grid_row: Optional[int] = None


class _RowRenderer:
    """数据行渲染引擎，owner 为 Table。"""

    def __init__(self, owner):
        self.owner = owner
        self._pool: list[_RowSlot] = []
        self._structure_sig = None          # 列 + 是否多选 的结构签名
        self._has_cb = False                # 当前结构是否含 checkbox 列
        self._col_offset = 0
        # 虚拟化 spacer（懒建）
        self._top_spacer: Optional[QWidget] = None
        self._bottom_spacer: Optional[QWidget] = None
        self._first_visible = 0             # 虚拟化：当前窗口首行在全量数据中的下标

    # ------------------------------------------------------------
    # 结构管理
    # ------------------------------------------------------------
    def _structure_signature(self):
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
        ws = list(slot.cells.values())
        if slot.checkbox_holder is not None:
            ws.append(slot.checkbox_holder)
        return ws

    def _ensure_structure(self):
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
        owner = self.owner
        grid = owner._grid
        slot = _RowSlot()
        grid_row = slot_index + 2  # +1 留给 header(row0)，+1 留给 top spacer(row1)

        if self._has_cb:
            # 必须带 parent=grid_host：无父 widget 会瞬间变顶层窗口，
            # Windows 上批量创建行槽时闪出一堆原生空白窗口。
            cb = Checkbox(color=owner._color, size=owner._size, theme="auto",
                          parent=owner._grid_host)
            cb.clicked.connect(
                lambda *_a, s=slot: owner._on_checkbox_clicked(s.row_key)
            )
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
                self._fill_slot(slot, keys[i], abs_index=i,
                                total=len(keys))
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
                self._fill_slot(slot, keys[abs_index], abs_index=abs_index,
                                total=total)
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
                color=owner._color, size=owner._size, theme=owner._theme,
                radius=owner._radius, is_striped=owner._is_striped,
                is_compact=owner._is_compact, is_multi=is_multi,
                align=col["align"], disable_animation=owner._disable_animation,
            )
            cell.set_position(
                is_first_row=(abs_index == 0), is_last_row=(abs_index == total - 1),
                is_first_col=(ci == 0), is_last_col=(ci == n_cols - 1),
            )
        if slot.checkbox is not None:
            slot.checkbox.set_color(owner._color)
            slot.checkbox.setEnabled(row_key not in owner._disabled_keys)

    def _show_slot(self, slot: _RowSlot, visible: bool):
        if not visible:
            slot.row_key = None
        for w in self._slot_widgets(slot):
            w.setVisible(visible)

    def _publish_maps(self, keys, rendered_indices):
        """把当前已渲染行的 cell / checkbox 暴露到 owner._cells / _row_checkboxes，
        让 owner 的 _apply_row_states / _propagate_style 等沿用原逻辑。
        只纳入仍持有 row_key 的行槽（隐藏槽 row_key 已被清空）。"""
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
        sp = QWidget(self.owner._grid_host)
        sp.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        span = max(1, len(self.owner._columns) + self._col_offset)
        self.owner._grid.addWidget(sp, grid_row, 0, 1, span)
        return sp

    def _set_spacers(self, top_h: int, bottom_h: int):
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
