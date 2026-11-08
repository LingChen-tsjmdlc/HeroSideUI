"""Table 选中状态机 mixin：none/single/multiple，支持 select-all 与必选堵截。"""

from __future__ import annotations


class _SelectionMixin:
    """表格选中状态机 mixin，管理 none/single/multiple 三种模式。"""

    def _selectable_keys(self) -> list:
        """返回未禁用的可选行 key 列表。"""
        return [k for k in self._row_order if k not in self._disabled_keys]

    def _on_row_clicked(self, key: str):
        """处理行点击，按选择模式更新选中项并发出信号。

        Args:
            key: 被点击的行 key。

        Note:
            none 模式只发 row_action；禁用行直接返回；必选模式下取消最后一项改为发出 row_action。
        """
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
        """切换全选状态并发出变更信号。

        Note:
            仅 multiple 模式生效；已全选时清空，但必选模式下保持不动。
        """
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
