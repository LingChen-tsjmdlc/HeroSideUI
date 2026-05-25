"""Listbox 键盘导航（mixin）。"""

from PySide6.QtCore import Qt


class _KeyboardNavMixin:
    """方向键 / Home / End / Enter / Space 的导航与激活。

    宿主必须提供：
        self._items, self._focused_index, self._on_item_activated
    """

    # 让 ListboxItem 转发上来的方向键统一从这里入；
    # 返回 True 表示已消费，调用方应 e.accept() 不再传播。
    def handle_nav_key(self, key) -> bool:
        if key in (Qt.Key_Down, Qt.Key_Up):
            self._move_focus(1 if key == Qt.Key_Down else -1)
            return True
        if key == Qt.Key_Home:
            self._set_focus_index(self._first_enabled_index())
            return True
        if key == Qt.Key_End:
            self._set_focus_index(self._last_enabled_index())
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
        # Listbox 自己拿到焦点时的兜底入口
        if self.handle_nav_key(e.key()):
            e.accept()
            return
        super().keyPressEvent(e)

    def focus_first_enabled(self):
        # 给外部（Select/Autocomplete popover 打开时）调用，把焦点落到第一个可用项
        idx = self._first_enabled_index()
        if idx >= 0:
            self._set_focus_index(idx)

    def _enabled_indices(self) -> list[int]:
        return [i for i, it in enumerate(self._items) if not it.is_disabled()]

    def _first_enabled_index(self) -> int:
        idxs = self._enabled_indices()
        return idxs[0] if idxs else -1

    def _last_enabled_index(self) -> int:
        idxs = self._enabled_indices()
        return idxs[-1] if idxs else -1

    def _move_focus(self, step: int):
        idxs = self._enabled_indices()
        if not idxs:
            return
        if self._focused_index < 0 or self._focused_index not in idxs:
            self._set_focus_index(idxs[0] if step > 0 else idxs[-1])
            return
        cur = idxs.index(self._focused_index)
        nxt = (cur + step) % len(idxs)
        self._set_focus_index(idxs[nxt])

    def _set_focus_index(self, idx: int):
        self._focused_index = idx
        if 0 <= idx < len(self._items):
            self._items[idx].setFocus(Qt.TabFocusReason)
