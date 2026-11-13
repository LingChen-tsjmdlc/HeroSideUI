"""Listbox 键盘导航（mixin）。"""

from PySide6.QtCore import Qt


class _KeyboardNavMixin:
    """方向键/Home/End/Enter/Space 导航 mixin；宿主提供条目与焦点字段。"""

    def handle_nav_key(self, key) -> bool:
        """处理方向键 / Home / End / 回车 / 空格 导航。

        Args:
            key: Qt.Key 枚举值，由 keyPressEvent 转发而来。

        Returns:
            bool: True 表示已消费该按键（调用方应 e.accept()），False 表示未处理。
        """
        if key in (Qt.Key_Down, Qt.Key_Up):
            self.move_focus(1 if key == Qt.Key_Down else -1)
            return True
        if key == Qt.Key_Home:
            self.set_focus_index(self.first_enabled_index())
            return True
        if key == Qt.Key_End:
            self.set_focus_index(self.last_enabled_index())
            return True
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if 0 <= self._focused_index < len(self._items):
                it = self._items[self._focused_index]
                if not it.is_disabled():
                    # 走 click 路径触发 QAbstractButton 内置 toggle + 守卫拦截
                    it.click()
            return True
        return False

    def keyPressEvent(self, e):
        """Listbox 自身拿到焦点时的键盘兜底入口。

        Args:
            e: QKeyEvent，先看是否命中导航键，命中则消费，否则上抛基类。
        """
        # Listbox 自己拿到焦点时的兜底入口
        if self.handle_nav_key(e.key()):
            e.accept()
            return
        super().keyPressEvent(e)

    def focus_first_enabled(self):
        """把焦点落到第一个可用（未禁用）项。"""
        idx = self.first_enabled_index()
        if idx >= 0:
            self.set_focus_index(idx)

    def focused_index(self) -> int:
        """返回键盘焦点项的索引，无焦点时为 -1。"""
        return self._focused_index

    def activate_focused(self) -> bool:
        """激活当前焦点项，等同于对其选中，禁用项除外。

        Returns:
            是否存在可激活的焦点项并已激活。
        """
        if not 0 <= self._focused_index < len(self._items):
            return False
        it = self._items[self._focused_index]
        if it.is_disabled():
            return False
        self._on_item_activated(it.key())
        return True

    def _enabled_indices(self) -> list[int]:
        """收集所有未禁用项的索引。

        Returns:
            list[int]: 可用项在 self._items 中的索引列表。
        """
        return [i for i, it in enumerate(self._items) if not it.is_disabled()]

    def first_enabled_index(self) -> int:
        """首个可用项的索引。

        Returns:
            int: 首个未禁用项索引；无可用项时返回 -1。
        """
        idxs = self._enabled_indices()
        return idxs[0] if idxs else -1

    def last_enabled_index(self) -> int:
        """末个可用项的索引。

        Returns:
            int: 最后一个未禁用项索引；无可用项时返回 -1。
        """
        idxs = self._enabled_indices()
        return idxs[-1] if idxs else -1

    def move_focus(self, step: int):
        """在可用项之间按步长循环移动焦点。

        Args:
            step: 移动步长，正数向下、负数向上；支持取模循环。
        """
        idxs = self._enabled_indices()
        if not idxs:
            return
        if self._focused_index < 0 or self._focused_index not in idxs:
            self.set_focus_index(idxs[0] if step > 0 else idxs[-1])
            return
        cur = idxs.index(self._focused_index)
        nxt = (cur + step) % len(idxs)
        self.set_focus_index(idxs[nxt])

    def set_focus_index(self, idx: int):
        """设置当前焦点项索引并真正把 Qt 焦点交给该项。

        Args:
            idx: 目标项索引；越界则仅更新记录不转移焦点。
        """
        self._focused_index = idx
        if 0 <= idx < len(self._items):
            self._items[idx].setFocus(Qt.TabFocusReason)
