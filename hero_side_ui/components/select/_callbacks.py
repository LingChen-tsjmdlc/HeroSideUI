"""Select 内部信号回调 mixin（私有）。"""

from PySide6.QtCore import QTimer

from ...themes import SELECT_SIZES


class _SelectCallbacksMixin:
    """Select 信号回调 mixin。"""

    # ============================================================
    # Listbox 选中变化
    # ============================================================
    def _on_listbox_action(self, key: str):
        """用户在 listbox 点击某项。"""
        # 单选 + 点击已选中项：listbox 默认不允许取消（HeroUI 对齐）；
        # 当 disallow_empty_selection=False 时主动允许回到空状态
        if (
            self._selection_mode == "single"
            and not self._disallow_empty_selection
            and key in self._selected_keys
        ):
            self._listbox.set_selected_keys(set())

        # 必选场景下 listbox 已在源头堵截"取消最后一个"，这里只做同步
        new_keys = set(self._listbox.selected_keys())
        changed = new_keys != self._selected_keys
        self._selected_keys = new_keys
        self._sync_trigger_text()
        self._refresh_clear_visibility()
        if changed:
            self.selection_changed.emit(self._emit_selection_payload())

        # 行为：single 选中后立刻关闭；multiple 保持打开
        if self._selection_mode == "single":
            self._just_committed = True
            self.close()
            QTimer.singleShot(200, lambda: setattr(self, "_just_committed", False))

    # ============================================================
    # Clear 按钮
    # ============================================================
    def _on_clear_clicked(self):
        if not self._selected_keys:
            return
        if self._disallow_empty_selection:
            return
        self._selected_keys = set()
        self._listbox.set_selected_keys(set())
        self._sync_trigger_text()
        self._refresh_clear_visibility()
        self.selection_changed.emit(self._emit_selection_payload())
        self.cleared.emit()
        # HeroUI 行为：clear 后焦点回 trigger
        QTimer.singleShot(0, self._input.line_edit.setFocus)

    # ============================================================
    # Selector 按钮（chevron）
    # ============================================================
    def _on_selector_clicked(self):
        if self._is_disabled:
            return
        self.toggle()
        QTimer.singleShot(0, self._input.line_edit.setFocus)

    # ============================================================
    # Popover open/close
    # ============================================================
    def _on_popover_open_changed(self, is_open: bool):
        self._is_open = is_open
        self._refresh_clear_visibility()
        if not self._disable_selector_icon_rotation:
            cfg = SELECT_SIZES.get(self._size, SELECT_SIZES["md"])
            self._end.selector_btn.set_angle(
                180.0 if is_open else 0.0,
                animated=not self._disable_animation,
                duration=cfg["rotate_duration"],
            )
        # 打开时滚到第一个选中项
        if is_open and self._selected_keys:
            first_key = next(iter(self._selected_keys))
            it = self._listbox.item_by_key(first_key)
            if it is not None and hasattr(self._scroll, "ensureWidgetVisible"):
                self._scroll.ensureWidgetVisible(it)
        if not is_open:
            self.closed.emit()
        self.open_changed.emit(is_open)
