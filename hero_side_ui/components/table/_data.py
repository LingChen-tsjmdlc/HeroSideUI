"""Table 数据装配 mixin：列定义/行增删/渲染回调，更新后触发 _rebuild。"""

from __future__ import annotations

from collections.abc import Callable

from ._constants import VALID_ALIGNS


class _DataMixin:
    """表格数据装配 mixin，负责列定义、行增删与渲染回调。"""

    # ------------------------------------------------------------
    # 列
    # ------------------------------------------------------------
    def set_columns(self, columns: list):
        """设置列定义；与当前一致时跳过重建（翻页场景优化）。"""
        normalized = []
        for col in columns:
            normalized.append(
                {
                    "key": col["key"],
                    "label": col.get("label", ""),
                    "align": col.get("align", "start")
                    if col.get("align") in VALID_ALIGNS
                    else "start",
                    "allows_sorting": bool(col.get("allows_sorting", False)),
                    "width": col.get("width"),
                }
            )
        if normalized == self._columns:
            return
        self._columns = normalized
        self._rebuild()

    def columns(self) -> list:
        """返回当前列定义的副本。"""
        return list(self._columns)

    # ------------------------------------------------------------
    # 行
    # ------------------------------------------------------------
    def add_row(self, key: str, cells, *, is_disabled: bool = False):
        """追加一行；cells 可为 dict 或 list，值可为 str 或 QWidget。"""
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
        """把行单元格归一化为按列 key 索引的字典。

        Args:
            cells: 单元格值；dict 直接复制，list 按列顺序映射。

        Returns:
            以列 key 为键的单元格字典。

        Note:
            list 按列顺序映射且用 strict=False，长度不匹配时静默截断，未做校验。
        """
        if isinstance(cells, dict):
            return dict(cells)
        # list：按列顺序映射
        result = {}
        for col, val in zip(self._columns, cells, strict=False):
            result[col["key"]] = val
        return result

    def clear(self):
        """清空所有行、选中项与悬停态并触发重建。"""
        self._row_order = []
        self._row_data = {}
        self._row_disabled_flags = {}
        self._selected_keys.clear()
        self._hover_key = None
        self._recompute_disabled()
        self._rebuild()

    def set_render_cell(self, fn: Callable | None):
        """设置自定义单元格渲染回调 ``fn(row_key, col_key, value) -> str | QWidget``。"""
        self._render_cell = fn
        self._rebuild()

    def rows(self) -> list:
        """返回当前行 key 顺序的副本。"""
        return list(self._row_order)

    def _make_cell_content(self, row_key: str, col_key: str):
        """按行与列 key 生成单元格内容。

        Args:
            row_key: 行 key。
            col_key: 列 key。

        Returns:
            原始值；设置了 _render_cell 时返回其回调结果。
        """
        value = self._row_data.get(row_key, {}).get(col_key, "")
        if self._render_cell is not None:
            return self._render_cell(row_key, col_key, value)
        return value
