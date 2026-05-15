"""Autocomplete 内部信号处理 mixin（私有）。

把 ``_on_input_changed`` / ``_on_listbox_action`` / ``_on_clear_clicked`` /
``_on_selector_clicked`` / ``_on_popover_open_changed`` 等所有内部回调
集中到一处，避免主组件文件被它们撑大。
"""

from ...themes import AUTOCOMPLETE_SIZES

from typing import Optional

from PySide6.QtCore import QTimer


class _AutocompleteCallbacksMixin:
    """Autocomplete 信号回调 mixin。"""

    # ============================================================
    # 事件
    # ============================================================
    def _on_input_changed(self, text: str):
        if self._programmatic_text:
            self._input_value = text
            return
        self._input_value = text
        # 用户键入 → 清除 selected_key（HeroUI 行为）
        if self._selected_key is not None:
            # 判断：如果新 text 还是当前 selected 的 label 不变（textChanged 重复触发），
            # 不要把 selected 清掉
            it = self._listbox.item_by_key(self._selected_key)
            if it is None or it.title() != text:
                self._selected_key = None
                self._listbox.set_selected_keys(set())
                self.selection_changed.emit(None)
        self._apply_filter()
        self._refresh_clear_visibility()
        # 打开 popover（typing trigger）
        if not self._is_open and self._menu_trigger != "manual":
            self.open(trigger="input")
        self.input_changed.emit(text)

    def _on_listbox_action(self, key: str):
        """用户在 listbox 点击某项。"""
        it = self._listbox.item_by_key(key)
        if it is None:
            return
        new_text = it.title()
        # 选中 key
        self._selected_key = key
        self._listbox.set_selected_keys({key})
        # 同步 input.text
        if new_text != self._input_value:
            self._programmatic_text = True
            self._input.set_text(new_text)
            self._input_value = new_text
            self._programmatic_text = False
            self.input_changed.emit(new_text)
        self._refresh_clear_visibility()
        self.selection_changed.emit(key)
        # 守卫位 _just_committed：让 Qt 在 popover 关闭时自动还焦点给 line_edit
        # 触发的 FocusIn 不会自动重开 popover。
        #
        # 关键设计：守卫不是按时间窗解锁，而是"事件序列"解锁 —— 只拦截
        # 接下来 line_edit 收到的第一个 FocusIn（即 Qt 自动 restore focus 那一发），
        # 命中后立刻解锁。这样无论用户手速多快、popover fade-out 多久，
        # 都不会误拦合法的"再次点击重开"操作。
        # 兜底：FocusIn 没来时（极端情况），200ms 后强制解锁，避免守卫卡死。
        self._just_committed = True
        self.close()
        QTimer.singleShot(200, lambda: setattr(self, "_just_committed", False))

    def _on_clear_clicked(self):
        self._selected_key = None
        self._listbox.set_selected_keys(set())
        self._programmatic_text = True
        self._input.set_text("")
        self._programmatic_text = False
        self._input_value = ""
        self._apply_filter()
        self._refresh_clear_visibility()
        self.selection_changed.emit(None)
        self.input_changed.emit("")
        self.cleared.emit()
        # 打开 popover + 焦点回 input（对齐 HeroUI 行为）
        if not self._is_open:
            self.open(trigger="clear")
        QTimer.singleShot(0, self._input.line_edit.setFocus)

    def _on_selector_clicked(self):
        if self._is_disabled:
            return
        self.toggle(trigger="manual")
        # 点击 selector 后焦点回 input
        QTimer.singleShot(0, self._input.line_edit.setFocus)

    def _on_popover_open_changed(self, is_open: bool, trigger: str):
        self._is_open = is_open
        # popover 打开/关闭都刷一次 clear:open 时即使无 hover 也保留(键盘流),
        # close 时若 hover 也没了就该收起。
        self._refresh_clear_visibility()
        # selector 图标旋转
        if not self._disable_selector_icon_rotation:
            cfg = AUTOCOMPLETE_SIZES.get(self._size, AUTOCOMPLETE_SIZES["md"])
            self._end.selector_btn.set_angle(
                180.0 if is_open else 0.0,
                animated=not self._disable_animation,
                duration=cfg["rotate_duration"],
            )
        # 打开时滚到选中项
        if is_open and self._selected_key is not None:
            # listbox 自己已经维护焦点；这里只确保选中项可见
            it = self._listbox.item_by_key(self._selected_key)
            if it is not None:
                (
                    self._scroll.ensureWidgetVisible(it)
                    if hasattr(self._scroll, "ensureWidgetVisible")
                    else None
                )
        # 关闭时处理 allows_custom_value
        if not is_open and not self._allows_custom_value:
            # 如果当前 input.text 不匹配任何 item.label，回退到 selected_key 的 label，
            # 没 selected_key 就清空
            current_text = self._input_value
            matched = False
            for it in self._listbox.items():
                if it.title() == current_text:
                    matched = True
                    break
            if not matched:
                if self._selected_key is not None:
                    it = self._listbox.item_by_key(self._selected_key)
                    if it is not None:
                        self._programmatic_text = True
                        self._input.set_text(it.title())
                        self._input_value = it.title()
                        self._programmatic_text = False
                        self.input_changed.emit(self._input_value)
                else:
                    if current_text:
                        self._programmatic_text = True
                        self._input.set_text("")
                        self._input_value = ""
                        self._programmatic_text = False
                        self.input_changed.emit("")
                self._apply_filter()
                self._refresh_clear_visibility()

        self.open_changed.emit(is_open, trigger)

