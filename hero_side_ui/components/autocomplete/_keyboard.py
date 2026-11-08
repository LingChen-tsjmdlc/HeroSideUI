"""Autocomplete 键盘导航 mixin：eventFilter 拦截方向键/Enter/Esc 并实现导航。"""

from PySide6.QtCore import QEvent, Qt

from ..listbox import ListboxItem


class _AutocompleteKeyboardMixin:
    """Autocomplete 键盘 mixin。"""

    # ============================================================
    # 键盘 / 焦点 拦截
    # ============================================================
    def eventFilter(self, obj, event):
        """拦截 line_edit 的焦点与键盘事件，驱动 popover 与导航。

        Args:
            obj: 被监听的 QObject（input 的 line_edit）。
            event: 当前事件。

        Returns:
            True 表示事件已消费不再传播；其余交回父类。

        Note:
            FocusIn 命中 _just_committed 守卫时只解锁不重开 popover；
            方向键 / Home / End / Enter / Esc 在 popover 打开时全部接管。
        """
        if obj is self._input.line_edit:
            etype = event.type()
            if etype == QEvent.FocusIn:
                # 守卫：commit 选中后 popover 关闭会把焦点还给 line_edit，
                # 触发的 FocusIn 不应该再自动重开 popover。
                # 命中即解锁 —— 守卫的使命是拦掉这一发自动 FocusIn,接下来
                # 用户的真实点击/键盘操作就是合法的,不应再被拦截。
                # focus 时刷新 clear 显隐(focus 也是显示触发条件之一)。
                self._refresh_clear_visibility()
                if self._just_committed:
                    self._just_committed = False
                    return super().eventFilter(obj, event)
                if self._menu_trigger == "focus" and not self._is_open and not self._is_disabled:
                    self.open(trigger="focus")
            elif etype == QEvent.FocusOut:
                # 失焦后:如果鼠标也不在自己上面,clear 应该收起来
                self._refresh_clear_visibility()
            elif etype == QEvent.MouseButtonRelease:
                # 点击已经持有焦点的 input 不会触发 FocusIn,但用户预期"再点一下
                # 就能把 popover 重新拉出来"。守卫位仍然先拦截(防止 commit 后立刻
                # 再次点击造成误触发);守卫期过后,只要 popover 是关的就重开。
                if (
                    not self._just_committed
                    and self._menu_trigger != "manual"
                    and not self._is_open
                    and not self._is_disabled
                    and not self._input._is_readonly
                    and event.button() == Qt.LeftButton
                ):
                    self.open(trigger="focus")
            elif etype == QEvent.KeyPress:
                key = event.key()
                if key in (Qt.Key_Down, Qt.Key_Up):
                    self._handle_arrow(key == Qt.Key_Down)
                    return True
                if key == Qt.Key_Home and self._is_open:
                    vis = self._visible_items()
                    if vis:
                        self._listbox._set_focus_index(self._listbox.items().index(vis[0]))
                    return True
                if key == Qt.Key_End and self._is_open:
                    vis = self._visible_items()
                    if vis:
                        self._listbox._set_focus_index(self._listbox.items().index(vis[-1]))
                    return True
                if key == Qt.Key_Escape:
                    if self._is_open:
                        self.close()
                        return True
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    if self._is_open:
                        # 优先选中焦点项；若无可选 + allows_custom_value 则提交
                        vis = self._visible_items()
                        if vis:
                            self._activate_focused_item()
                            return True
                        if self._allows_custom_value:
                            self.submitted.emit(self._input_value)
                            self.close()
                            return True
                    elif self._allows_custom_value:
                        # popover 已关 + custom value：直接提交
                        self.submitted.emit(self._input_value)
                        return True
        return super().eventFilter(obj, event)

    def _visible_items(self) -> list[ListboxItem]:
        """返回当前可见且未禁用的 listbox 项。

        Returns:
            可见项列表，顺序与 items() 一致。

        Note:
            用 not isHidden() 而非 isVisible() —— popover 关闭时 isVisible
            会因祖先 hide 返回 False，而 hide_state（被 _apply_filter 隐藏）
            才是导航关心的语义。
        """
        # 用 not isHidden() 而非 isVisible() —— popover 关闭时 isVisible 会因祖先 hide
        # 返回 False，但 hide_state（即被 _apply_filter setVisible(False)）才是我们关心的
        return [it for it in self._listbox.items() if not it.isHidden() and not it.is_disabled()]

    def _handle_arrow(self, down: bool):
        """处理上 / 下方向键的焦点导航。

        Args:
            down: True 为向下移动，False 为向上。

        Note:
            popover 关闭时先打开并聚焦第一个可见项；无焦点项时向下落到
            首项、向上落到末项；其余情况在可见项内循环移动。
        """
        if not self._is_open:
            self.open(trigger="input")
            # 第一个可见项默认聚焦
            vis = self._visible_items()
            if vis:
                self._listbox._set_focus_index(self._listbox.items().index(vis[0]))
            return
        vis = self._visible_items()
        if not vis:
            return
        # 找当前焦点项在 vis 中的位置
        cur_idx = -1
        for i, it in enumerate(vis):
            if it.hasFocus():
                cur_idx = i
                break
        if cur_idx < 0:
            nxt = 0 if down else len(vis) - 1
        else:
            nxt = (cur_idx + (1 if down else -1)) % len(vis)
        target = vis[nxt]
        self._listbox._set_focus_index(self._listbox.items().index(target))

    def _activate_focused_item(self):
        """激活（提交）当前有焦点的可见项。

        Note:
            无焦点项时退化为第一个可见项，与方向键导航的初始聚焦一致。
        """
        vis = self._visible_items()
        if not vis:
            return
        focused = None
        for it in vis:
            if it.hasFocus():
                focused = it
                break
        if focused is None:
            focused = vis[0]
        self._on_listbox_action(focused.key())
