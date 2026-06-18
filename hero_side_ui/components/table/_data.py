"""Table 数据装配 API（mixin）：列定义 / 行增删 / 渲染回调。

把 set_columns / add_row / set_rows / clear / set_render_cell 等数据入口从主体抽出。
这些方法负责更新内部数据状态后触发 ``_rebuild``。

宿主 Table 需提供：_columns/_row_order/_row_data/_row_disabled_flags/
_render_cell/_selected_keys/_user_disabled_keys/_disabled_keys/_hover_key
以及 _rebuild 方法。
"""

from __future__ import annotations

from typing import Callable, Optional

from ._constants import VALID_ALIGNS


class _DataMixin:
    # ------------------------------------------------------------
    # 列
    # ------------------------------------------------------------
    def set_columns(self, columns: list):
        """设置列定义。

        每列是 dict：``{"key", "label", "align"?, "allows_sorting"?, "width"?}``。
        列定义与当前完全一致时跳过重建（翻页/刷新常重复传同一份列，避免白白全量重建）。
        """
        normalized = []
        for col in columns:
            normalized.append(
                {
                    "key": col["key"],
                    "label": col.get("label", ""),
                    "align": col.get("align", "start") if col.get("align") in VALID_ALIGNS else "start",
                    "allows_sorting": bool(col.get("allows_sorting", False)),
                    "width": col.get("width"),
                }
            )
        if normalized == self._columns:
            return
        self._columns = normalized
        self._rebuild()

    def columns(self) -> list:
        return list(self._columns)

    # ------------------------------------------------------------
    # 行
    # ------------------------------------------------------------
    def add_row(self, key: str, cells, *, is_disabled: bool = False):
        """追加一行。

        ``cells`` 可为 dict（col_key -> 值）或 list（按列顺序）。值可为 str 或 QWidget。
        若设置了 render_cell 回调，则忽略此处传入值的渲染，交由回调生成内容。
        """
        key = str(key)
        if key in self._row_data:
            return
        self._row_order.append(key)
        self._row_data[key] = self._normalize_cells(cells)
        self._row_disabled_flags[key] = bool(is_disabled)
        self._recompute_disabled()
        self._rebuild()

    def set_rows(self, rows: list):
        """批量设置行。每行 dict 需含 'key'，其余为列值；可选 '_disabled'。"""
        self._row_order = []
        self._row_data = {}
        self._row_disabled_flags = {}
        # 仅保留落在新行集合内的选中项，避免翻页/换数据后残留已不存在的 key
        new_keys = set()
        for row in rows:
            key = str(row.get("key"))
            new_keys.add(key)
            self._row_order.append(key)
            data = {k: v for k, v in row.items() if k not in ("key", "_disabled")}
            self._row_data[key] = data
            self._row_disabled_flags[key] = bool(row.get("_disabled", False))
        self._selected_keys &= new_keys
        self._recompute_disabled()
        self._rebuild()

    def _recompute_disabled(self):
        """重算 _disabled_keys = 用户显式禁用 ∪ 行内联禁用标志。"""
        inline = {k for k, v in self._row_disabled_flags.items() if v}
        self._disabled_keys = set(self._user_disabled_keys) | inline

    def _normalize_cells(self, cells) -> dict:
        if isinstance(cells, dict):
            return dict(cells)
        # list：按列顺序映射
        result = {}
        for col, val in zip(self._columns, cells):
            result[col["key"]] = val
        return result

    def clear(self):
        self._row_order = []
        self._row_data = {}
        self._row_disabled_flags = {}
        self._selected_keys.clear()
        self._hover_key = None
        self._recompute_disabled()
        self._rebuild()

    def set_render_cell(self, fn: Optional[Callable]):
        """设置自定义单元格渲染回调 ``fn(row_key, col_key, value) -> str | QWidget``。"""
        self._render_cell = fn
        self._rebuild()

    def rows(self) -> list:
        return list(self._row_order)

    def _make_cell_content(self, row_key: str, col_key: str):
        value = self._row_data.get(row_key, {}).get(col_key, "")
        if self._render_cell is not None:
            return self._render_cell(row_key, col_key, value)
        return value
