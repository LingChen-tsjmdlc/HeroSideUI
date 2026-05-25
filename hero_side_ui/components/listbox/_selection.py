"""Listbox 选中状态机（mixin）。"""


class _SelectionMixin:
    """点击选中切换 + 必选堵截规则。

    宿主必须提供：
        self._selection_mode, self._selected_keys, self._items,
        self._disallow_empty_selection, self.item_by_key,
        self.selection_changed (Signal), self.action (Signal)
    """

    def _on_item_activated(self, key: str):
        # 必选语义：禁止把最后一项取消（多选剩 1 + 点的就是它，单选已天然 pass）
        if (
            self._disallow_empty_selection
            and self._selection_mode == "multiple"
            and key in self._selected_keys
            and len(self._selected_keys) == 1
        ):
            return

        if self._selection_mode == "single":
            old = set(self._selected_keys)
            if key in self._selected_keys:
                # HeroUI 默认对齐：单选点击已选项保持选中
                pass
            else:
                self._selected_keys = {key}
                for it in self._items:
                    it.set_selected(it.key() == key)
            if old != self._selected_keys:
                self.selection_changed.emit(set(self._selected_keys))
        elif self._selection_mode == "multiple":
            old = set(self._selected_keys)
            if key in self._selected_keys:
                self._selected_keys.remove(key)
                it = self.item_by_key(key)
                if it:
                    it.set_selected(False)
            else:
                self._selected_keys.add(key)
                it = self.item_by_key(key)
                if it:
                    it.set_selected(True)
            if old != self._selected_keys:
                self.selection_changed.emit(set(self._selected_keys))

        # action 在每次点击都触发
        self.action.emit(key)

    def _should_block_item_toggle(self, it) -> bool:
        # 必选下：点击会让 selection 变空时返回 True
        if not self._disallow_empty_selection:
            return False
        if self._selection_mode == "single":
            return it.key() in self._selected_keys
        if self._selection_mode == "multiple":
            return it.key() in self._selected_keys and len(self._selected_keys) == 1
        return False
