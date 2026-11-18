"""Dialog 的按钮区：按钮规格解析、角色与结果码、对齐与排序。"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QMetaObject, Signal
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QSizePolicy, QWidget

from ...themes import DIALOG_SPEC
from ...utils import safe_delete
from ..button import Button

ACCEPTED = 1
REJECTED = 0
_NAMED_ROLES = {"accept": ACCEPTED, "reject": REJECTED, "none": None}


def check_code(code) -> int:
    """结果码必须是整数；bool 不算（True 会和 1 混淆）。

    Raises:
        ValueError: 不是整数。
    """
    if isinstance(code, bool) or not isinstance(code, int):
        raise ValueError(f"result code must be an int (not bool), got {code!r}")
    return code


def parse_role(role) -> int | None:
    """角色转结果码。

    Args:
        role: accept（1）/ reject（0）/ none（点击不关闭）/ 任意整数。

    Returns:
        结果码；None 表示点击后不关闭。

    Raises:
        ValueError: 不认识的字符串或非整数。
    """
    if isinstance(role, str):
        if role not in _NAMED_ROLES:
            raise ValueError(f"role must be one of {tuple(_NAMED_ROLES)} or an int, got {role!r}")
        return _NAMED_ROLES[role]
    return check_code(role)


def parse_item(item) -> tuple[str | QAbstractButton, int | None, object]:
    """解析一个按钮规格。

    Args:
        item: Button / (文字或 Button, 角色) / (文字或 Button, 角色, 数据)。

    Returns:
        (文字或按钮, 结果码, 结果数据)。

    Raises:
        ValueError: 写法不对或角色非法。
    """
    if isinstance(item, QAbstractButton):
        return item, None, None
    if isinstance(item, (tuple, list)) and len(item) in (2, 3):
        first = item[0]
        if not isinstance(first, (str, QAbstractButton)):
            raise ValueError(f"button must be str or a button widget, got {first!r}")
        return first, parse_role(item[1]), (item[2] if len(item) == 3 else None)
    raise ValueError(f"invalid footer item: {item!r}")


@dataclass
class _Entry:
    """一个按钮及其点击后的行为。"""

    button: QAbstractButton
    code: int | None
    data: object
    own: bool  # 由 Dialog 创建，样式随语义色联动
    policy: QSizePolicy
    conn: QMetaObject.Connection | None = None


class _Footer(QWidget):
    """按钮区：按角色决定样式、点击行为与排列顺序。

    Attributes:
        activated: 点击带结果码的按钮时发出 (结果码, 结果数据)。
    """

    activated = Signal(int, object)

    def __init__(self, parent: QWidget | None = None):
        """创建空的按钮区（无按钮时隐藏）。"""
        super().__init__(parent)
        self._entries: list[_Entry] = []
        self._align = "end"
        self._order = "auto"
        self._color = "primary"
        self._theme = "auto"
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(
            DIALOG_SPEC["padding_x"],
            DIALOG_SPEC["footer_padding_top"],
            DIALOG_SPEC["padding_x"],
            DIALOG_SPEC["footer_padding_bottom"],
        )
        self._lay.setSpacing(DIALOG_SPEC["footer_gap"])
        self.hide()

    # ---- 读取 ----
    def is_empty(self) -> bool:
        """是否没有按钮。"""
        return not self._entries

    def buttons(self) -> list[QAbstractButton]:
        """按创建顺序返回全部按钮。"""
        return [e.button for e in self._entries]

    def default_button(self, explicit: QAbstractButton | None) -> QAbstractButton | None:
        """Enter 触发的按钮：显式指定且仍在按钮区内的优先，否则取第一个 reject 角色的按钮。"""
        if explicit is not None and any(e.button is explicit for e in self._entries):
            return explicit
        for e in self._entries:
            if e.code == REJECTED:
                return e.button
        return None

    # ---- 配置 ----
    def configure(
        self,
        *,
        align: str | None = None,
        order: str | None = None,
        color: str | None = None,
        theme: str | None = None,
    ):
        """更新对齐、排序、主按钮语义色与主题，并刷新。没传的保持不变。"""
        if align is not None:
            self._align = align
        if order is not None:
            self._order = order
        if color is not None:
            self._color = color
        if theme is not None:
            self._theme = theme
        for e in self._entries:
            self._style(e)
        self._relayout()

    # ---- 增删 ----
    def set_items(self, items: list):
        """用一组按钮规格替换全部按钮；写法有误时抛错且不改动现有按钮。

        Raises:
            ValueError: 任一项写法或角色非法。
        """
        parsed = [parse_item(i) for i in items]
        keep = {id(p[0]) for p in parsed if isinstance(p[0], QAbstractButton)}
        self._clear(keep)
        for first, code, data in parsed:
            self._append(first, code, data)
        self._relayout()

    def add_item(self, button: str | QAbstractButton, role="none", data=None) -> QAbstractButton:
        """追加一个按钮。

        Args:
            button: 文字（Dialog 创建按钮）或自己的按钮。
            role: accept / reject / none / 整数。
            data: 点击时附带的结果数据。

        Returns:
            加入的按钮。
        """
        parse_item((button, role, data))
        entry = self._append(button, parse_role(role), data)
        self._relayout()
        return entry.button

    def _clear(self, keep: set[int]):
        """移除全部按钮；id 在 keep 里的只断开点击连接，不销毁。"""
        for e in self._entries:
            if e.conn is not None:
                try:
                    e.button.clicked.disconnect(e.conn)
                except (RuntimeError, TypeError):
                    pass  # 按钮已被外部销毁
            if id(e.button) not in keep:
                safe_delete(e.button)
        self._entries = []

    def _append(self, first: str | QAbstractButton, code: int | None, data) -> _Entry:
        """创建 / 收养一个按钮并登记。"""
        own = isinstance(first, str)
        btn = Button(first, size="md", theme=self._theme, parent=self) if own else first
        btn.setParent(self)
        entry = _Entry(btn, code, data, own, QSizePolicy(btn.sizePolicy()))
        if code is not None:
            entry.conn = btn.clicked.connect(lambda *_, e=entry: self._fire(e))
        self._entries.append(entry)
        self._style(entry)
        btn.show()
        return entry

    def _fire(self, entry: _Entry):
        """按钮被点击：把它的结果码与数据交给 Dialog。"""
        self.activated.emit(entry.code, entry.data)

    # ---- 样式与排列 ----
    def _style(self, entry: _Entry):
        """Dialog 创建的按钮：accept 为实心语义色，其余为浅色。"""
        if not entry.own:
            return
        btn = entry.button
        if entry.code == ACCEPTED:
            btn.set_color(self._color)
            btn.set_variant("solid")
        else:
            btn.set_color("default")
            btn.set_variant("flat")
        btn.set_theme(self._theme)

    def _display_order(self) -> list[_Entry]:
        """按 button_order 排出显示顺序：只有 accept 角色的按钮前移或后移；auto 等于 cancel_first。"""
        order = "cancel_first" if self._order == "auto" else self._order
        accept = [e for e in self._entries if e.code == ACCEPTED]
        rest = [e for e in self._entries if e.code != ACCEPTED]
        return accept + rest if order == "ok_first" else rest + accept

    def _relayout(self):
        """按对齐与排序重排按钮；没有按钮时整个按钮区隐藏。"""
        while self._lay.count():
            self._lay.takeAt(0)
        stretch = self._align == "stretch"
        if self._align in ("end", "center"):
            self._lay.addStretch(1)
        for e in self._display_order():
            if stretch:
                e.button.setSizePolicy(QSizePolicy.Policy.Expanding, e.policy.verticalPolicy())
            else:
                e.button.setSizePolicy(e.policy)
            self._lay.addWidget(e.button, 1 if stretch else 0)
        if self._align in ("start", "center"):
            self._lay.addStretch(1)
        self.setHidden(not self._entries)
        self._lay.invalidate()


__all__ = ["ACCEPTED", "REJECTED", "_Footer", "check_code", "parse_item", "parse_role"]
