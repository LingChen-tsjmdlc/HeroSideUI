"""Table 选中状态机（mixin）。

对齐 HeroUI v2 selectionMode：none / single / multiple。
single 点击行即选中（点已选项保持）；multiple 点击切换，支持 select-all。
disallow_empty_selection 时禁止取消最后一项。

宿主必须提供：
    self._selection_mode (str), self._selected_keys (set[str]),
    self._disabled_keys (set[str]), self._row_order (list[str] 行 key 顺序),
    self._disallow_empty_selection (bool),
    self.selection_changed (Signal(set)), self.row_action (Signal(str)),
    self._apply_row_states() —— 重绘所有行的选中 / hover 视觉。
"""

from __future__ import annotations


class _SelectionMixin:
    def _selectable_keys(self) -> list:
        return [k for k in self._row_order if k not in self._disabled_keys]

    def _on_row_clicked(self, key: str):
        if self._selection_mode == "none":
            self.row_action.emit(key)
            return
        if key in self._disabled_keys:
            return

        old = set(self._selected_keys)

        if self._selection_mode == "single":
            if key not in self._selected_keys:
                self._selected_keys = {key}
        else:  # multiple
            if key in self._selected_keys:
                # 必选堵截：不能取消最后一项
                if self._disallow_empty_selection and len(self._selected_keys) == 1:
                    self.row_action.emit(key)
                    return
                self._selected_keys.discard(key)
            else:
                self._selected_keys.add(key)

        if old != self._selected_keys:
            self._apply_row_states()
            self.selection_changed.emit(set(self._selected_keys))
        self.row_action.emit(key)

    def _toggle_select_all(self):
        if self._selection_mode != "multiple":
            return
        old = set(self._selected_keys)
        selectable = set(self._selectable_keys())
        if self._selected_keys >= selectable and selectable:
            # 全选状态 → 清空（受必选约束则保留一项）
            if self._disallow_empty_selection:
                return
            self._selected_keys = set()
        else:
            self._selected_keys = set(selectable)
        if old != self._selected_keys:
            self._apply_row_states()
            self.selection_changed.emit(set(self._selected_keys))

    def _select_all_state(self) -> str:
        """返回 'all' / 'none' / 'partial'，供 select-all checkbox 显示。"""
        selectable = set(self._selectable_keys())
        if not selectable:
            return "none"
        sel = self._selected_keys & selectable
        if sel == selectable:
            return "all"
        if not sel:
            return "none"
        return "partial"
