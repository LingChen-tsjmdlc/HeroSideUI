"""ListboxSection — 列表分组容器（带可选 heading 与底部 divider）。"""

from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from ...core import StatePalette
from ...themes import LISTBOX_SIZES

from ..text import Text
from .item import ListboxItem

# ============================================================
# ListboxSection
# ============================================================


class ListboxSection(QWidget):
    """分组容器。

    用法::

        sec = ListboxSection("Actions", show_divider=True)
        sec.add_item("Copy", key="copy")
        sec.add_item("Paste", key="paste")
        listbox.add_section(sec)
    """

    def __init__(
        self,
        title: str = "",
        *,
        show_divider: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._title = title
        self._show_divider = show_divider

        self._theme = "light"
        self._size = "md"

        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(0, 0, 0, 0)
        self._v.setSpacing(0)

        # heading
        self._heading = Text(title, parent=self, selectable=False)
        self._heading.setAttribute(Qt.WA_TranslucentBackground, True)
        self._v.addWidget(self._heading)
        if not title:
            self._heading.hide()

        # group
        self._group = QWidget(self)
        self._group.setAttribute(Qt.WA_TranslucentBackground, True)
        self._group_v = QVBoxLayout(self._group)
        self._group_v.setContentsMargins(0, 0, 0, 0)
        self._v.addWidget(self._group)

        # divider 区域
        self._has_divider_painted = False

        self._items: list[ListboxItem] = []

    def title(self) -> str:
        return self._title

    def set_title(self, t: str):
        self._title = t
        self._heading.setText(t)
        self._heading.setVisible(bool(t))

    def show_divider(self) -> bool:
        return self._show_divider

    def set_show_divider(self, v: bool):
        self._show_divider = bool(v)
        self.update()

    def add_item(self, item_or_title, **kwargs) -> ListboxItem:
        """添加一项；可以传 ListboxItem 或 (title, **kwargs)"""
        if isinstance(item_or_title, ListboxItem):
            it = item_or_title
        else:
            it = ListboxItem(item_or_title, **kwargs)
        self._items.append(it)
        self._group_v.addWidget(it)
        # 父 Listbox 在 add_section 后会调 _propagate_style 注入样式
        return it

    def items(self) -> list[ListboxItem]:
        return list(self._items)

    def _apply_style(
        self,
        *,
        variant: str,
        color: str,
        size: str,
        radius: str,
        theme: str,
        disable_animation: bool,
        hide_selected_icon: bool,
        highlight_on_focus: bool,
        selectable: bool,
    ):
        self._theme = theme
        self._size = size

        cfg = LISTBOX_SIZES.get(size, LISTBOX_SIZES["md"])
        self._v.setSpacing(0)
        self._group_v.setSpacing(cfg["list_gap"])

        # heading 样式：text-tiny + text-foreground-500
        self._heading.set_size(cfg["desc_font_size"])
        self._heading.set_color(StatePalette.text_description(theme).name())
        # 原 QSS padding: 0 Xpx → 走 contentsMargins。
        pad = cfg["item_padding_x"] // 2
        self._heading.setContentsMargins(pad, 0, pad, 0)
        # 顶部 padding：has-title=true:pt-1
        if self._title:
            self._group.setContentsMargins(0, 4, 0, 0)
        else:
            self._group.setContentsMargins(0, 0, 0, 0)

        # 底部 margin: mb-2 + divider mt-2 ≈ 8 + 8
        self._v.setContentsMargins(0, 0, 0, 8 if not self._show_divider else 16)

        # 把样式向下传给所有 item
        for it in self._items:
            it.apply_style(
                variant=variant,
                color=color,
                size=size,
                radius=radius,
                theme=theme,
                disable_animation=disable_animation,
                hide_selected_icon=hide_selected_icon,
                highlight_on_focus=highlight_on_focus,
                selectable=selectable,
            )

        self.update()

    def paintEvent(self, e):
        if not self._show_divider:
            return
        from PySide6.QtGui import QPen

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(StatePalette.divider(self._theme))
        pen.setWidth(1)
        p.setPen(pen)
        # 在 section 底部一行
        y = self.height() - 8
        p.drawLine(0, y, self.width(), y)
        p.end()
