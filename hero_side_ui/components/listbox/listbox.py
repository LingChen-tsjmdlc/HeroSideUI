"""HeroSideUI Listbox 主容器。

结构::

    Listbox (QWidget)
        ├── topContent     (可选)
        ├── _list (list slot)
        │     ├── ListboxItem / ListboxSection ...
        │     └── _empty_widget (默认隐藏)
        └── bottomContent  (可选)

子模块:
    item.py / section.py / _empty.py / _keyboard.py / _selection.py
"""

from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...core import ThemeProvider
from ...themes import LISTBOX_SIZES, RADIUS

from ..text import Text
from ._empty import _EmptyContentMixin
from ._keyboard import _KeyboardNavMixin
from ._selection import _SelectionMixin
from .item import ListboxItem
from .section import ListboxSection


class Listbox(_KeyboardNavMixin, _SelectionMixin, _EmptyContentMixin, QWidget):
    """HeroUI 风格列表框。

    用法::

        lb = Listbox(variant="flat", color="primary", selection_mode="single")
        lb.add_item("New", key="new", description="Create a new file")
        lb.action.connect(lambda key: print("activated", key))
    """

    selection_changed = Signal(set)
    action = Signal(str)
    open_changed = Signal(bool)  # 预留

    VALID_VARIANTS = ("solid", "shadow", "bordered", "flat", "faded", "light")
    VALID_COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
    VALID_SIZES = ("sm", "md", "lg")
    VALID_SELECTION_MODES = ("none", "single", "multiple")

    def __init__(
        self,
        *,
        variant: str = "solid",
        color: str = "default",
        size: str = "md",
        radius: str = "sm",
        selection_mode: str = "none",
        selected_keys: Optional[Iterable[str]] = None,
        disabled_keys: Optional[Iterable[str]] = None,
        disallow_empty_selection: bool = False,
        empty_content: Optional[str] = None,
        hide_selected_icon: bool = False,
        should_highlight_on_focus: bool = False,
        disable_animation: bool = False,
        is_disabled: bool = False,
        top_content: Optional[QWidget] = None,
        bottom_content: Optional[QWidget] = None,
        theme: str = "auto",
        parent=None,
    ):
        super().__init__(parent)

        if variant not in self.VALID_VARIANTS:
            variant = "solid"
        if color not in self.VALID_COLORS:
            color = "default"
        if size not in self.VALID_SIZES:
            size = "md"
        if selection_mode not in self.VALID_SELECTION_MODES:
            selection_mode = "none"

        self._variant = variant
        self._color = color
        self._size = size
        self._radius = radius
        self._selection_mode = selection_mode
        self._disallow_empty_selection = bool(disallow_empty_selection)
        self._hide_selected_icon = hide_selected_icon
        self._highlight_on_focus = should_highlight_on_focus
        self._disable_animation = disable_animation
        self._is_disabled = is_disabled
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._selected_keys: set[str] = set(selected_keys or [])
        self._disabled_keys: set[str] = set(disabled_keys or [])

        # 外层 layout = base slot (gap-1, p-1)
        self._outer = QVBoxLayout(self)
        cfg = LISTBOX_SIZES.get(size, LISTBOX_SIZES["md"])
        self._outer.setContentsMargins(
            cfg["list_padding"],
            cfg["list_padding"],
            cfg["list_padding"],
            cfg["list_padding"],
        )
        self._outer.setSpacing(cfg["group_gap"])

        self._top_content: Optional[QWidget] = None
        if top_content is not None:
            self.set_top_content(top_content)

        # list 容器
        self._list = QWidget(self)
        self._list.setAttribute(Qt.WA_TranslucentBackground, True)
        self._list_v = QVBoxLayout(self._list)
        self._list_v.setContentsMargins(0, 0, 0, 0)
        self._list_v.setSpacing(cfg["list_gap"])
        self._outer.addWidget(self._list)

        # emptyContent：None/"" 走默认 icon + 中英双语；非空 str 单行文字
        self._empty_content_text = empty_content
        self._empty_widget: QWidget = (
            QWidget()
        )  # 占位，立刻被 _rebuild_empty_widget 替换
        self._list_v.addWidget(self._empty_widget)
        self._empty_label: "Text" = Text("")
        self._rebuild_empty_widget()
        self._empty_widget.hide()
        # 末尾 stretch：让 items 在父容器给的高度大于实际总高时顶部对齐
        self._list_v.addStretch(1)

        self._bottom_content: Optional[QWidget] = None
        if bottom_content is not None:
            self.set_bottom_content(bottom_content)

        self._items: list[ListboxItem] = []
        self._sections: list[ListboxSection] = []

        self._focused_index = -1  # 键盘导航焦点

        self.setFocusPolicy(Qt.StrongFocus)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._propagate_style()
        self._refresh_empty()

    # ------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------
    def _resolve_theme(self, mode: str) -> str:
        if mode == "auto":
            return ThemeProvider.instance().current_theme
        return mode if mode in ("light", "dark") else "light"

    def _apply_provider_theme(self, theme: str):
        if self._theme_mode != "auto":
            return
        self._theme = theme
        self._propagate_style()
        # _empty_widget 的 icon pixmap + 文字 stylesheet 是构造时 cache 的，
        # 主题切换必须显式重建一遍，否则 dark 下还是 light 配色
        self._rebuild_empty_widget()
        self.update()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            ThemeProvider.instance().register(self)
            self._theme = ThemeProvider.instance().current_theme
        elif theme in ("light", "dark"):
            self._theme_mode = theme
            self._theme = theme
        else:
            return
        self._propagate_style()
        self.update()

    # ------------------------------------------------------------
    # 装配 API
    # ------------------------------------------------------------
    def set_top_content(self, w: Optional[QWidget]):
        if self._top_content is not None:
            self._outer.removeWidget(self._top_content)
            self._top_content.setParent(None)
            self._top_content.deleteLater()
            self._top_content = None
        if w is not None:
            self._top_content = w
            self._outer.insertWidget(0, w)

    def set_bottom_content(self, w: Optional[QWidget]):
        if self._bottom_content is not None:
            self._outer.removeWidget(self._bottom_content)
            self._bottom_content.setParent(None)
            self._bottom_content.deleteLater()
            self._bottom_content = None
        if w is not None:
            self._bottom_content = w
            self._outer.addWidget(w)

    def add_item(
        self,
        item_or_title,
        *,
        key: Optional[str] = None,
        description: str = "",
        start_content=None,
        end_content=None,
        shortcut: str = "",
        is_disabled: bool = False,
        show_divider: bool = False,
    ) -> ListboxItem:
        """追加一项；接受 ``ListboxItem`` 或 ``str`` (title)。"""
        if isinstance(item_or_title, ListboxItem):
            it = item_or_title
        else:
            it = ListboxItem(
                item_or_title,
                key=key,
                description=description,
                start_content=start_content,
                end_content=end_content,
                shortcut=shortcut,
                is_disabled=is_disabled,
                show_divider=show_divider,
            )
        self._attach_item(it)
        # 插到 _empty_widget 之前；_empty_label 是 _empty_widget 内部子项 indexOf 永远 -1
        idx = self._list_v.indexOf(self._empty_widget)
        if idx < 0:
            self._list_v.insertWidget(self._list_v.count() - 1, it)  # stretch 之前
        else:
            self._list_v.insertWidget(idx, it)
        self._items.append(it)
        self._propagate_style()
        self._refresh_empty()
        return it

    def add_section(
        self, sec_or_title, *, show_divider: bool = False
    ) -> ListboxSection:
        if isinstance(sec_or_title, ListboxSection):
            sec = sec_or_title
        else:
            sec = ListboxSection(sec_or_title, show_divider=show_divider)
        for it in sec.items():
            self._attach_item(it)
            self._items.append(it)

        idx = self._list_v.indexOf(self._empty_widget)
        if idx < 0:
            self._list_v.insertWidget(self._list_v.count() - 1, sec)
        else:
            self._list_v.insertWidget(idx, sec)
        self._sections.append(sec)
        self._propagate_style()
        self._refresh_empty()
        return sec

    def clear(self):
        for it in list(self._items):
            it.setParent(None)
            it.deleteLater()
        self._items.clear()
        for sec in list(self._sections):
            sec.setParent(None)
            sec.deleteLater()
        self._sections.clear()
        self._selected_keys.clear()
        self._refresh_empty()

    def items(self) -> list[ListboxItem]:
        return list(self._items)

    def item_by_key(self, key: str) -> Optional[ListboxItem]:
        for it in self._items:
            if it.key() == key:
                return it
        return None

    def _attach_item(self, it: ListboxItem):
        if it.key() in self._disabled_keys:
            it.set_disabled(True)
        if it.key() in self._selected_keys and self._selection_mode != "none":
            it.set_selected(True)
        # 注入"点击是否被拒"判定 —— 必选场景下从源头阻断 Qt 内置 toggle
        it._toggle_guard = self._should_block_item_toggle
        it.activated.connect(self._on_item_activated)

    # ------------------------------------------------------------
    # 选中 / 禁用 API
    # ------------------------------------------------------------
    def selection_mode(self) -> str:
        return self._selection_mode

    def set_selection_mode(self, mode: str):
        if mode not in self.VALID_SELECTION_MODES:
            return
        self._selection_mode = mode
        if mode == "none":
            self._selected_keys.clear()
            for it in self._items:
                it.set_selected(False)
        self._propagate_style()

    def disallow_empty_selection(self) -> bool:
        return self._disallow_empty_selection

    def set_disallow_empty_selection(self, v: bool):
        self._disallow_empty_selection = bool(v)

    def selected_keys(self) -> set[str]:
        return set(self._selected_keys)

    def set_selected_keys(self, keys: Iterable[str]):
        keys = set(keys)
        if self._selection_mode == "none":
            return
        if self._selection_mode == "single" and len(keys) > 1:
            keys = {next(iter(keys))}

        old = set(self._selected_keys)
        self._selected_keys = keys

        for it in self._items:
            want = it.key() in keys
            if it.is_selected() != want:
                it.set_selected(want)
        if old != keys:
            self.selection_changed.emit(set(self._selected_keys))

    def disabled_keys(self) -> set[str]:
        return set(self._disabled_keys)

    def set_disabled_keys(self, keys: Iterable[str]):
        self._disabled_keys = set(keys)
        for it in self._items:
            it.set_disabled(it.key() in self._disabled_keys)

    def is_disabled(self) -> bool:
        return self._is_disabled

    def set_is_disabled(self, v: bool):
        self._is_disabled = bool(v)
        # opacity effect 一刀切，不动 enabled 保留键盘焦点语义
        if not hasattr(self, "_disabled_effect"):
            self._disabled_effect = QGraphicsOpacityEffect(self)
        self._disabled_effect.setOpacity(0.5 if self._is_disabled else 1.0)
        self.setGraphicsEffect(self._disabled_effect if self._is_disabled else None)
        for it in self._items:
            it.setEnabled(not self._is_disabled and it.key() not in self._disabled_keys)

    # ------------------------------------------------------------
    # 动态属性 setter
    # ------------------------------------------------------------
    def set_variant(self, v: str):
        if v not in self.VALID_VARIANTS:
            return
        self._variant = v
        self._propagate_style()

    def set_color(self, c: str):
        if c not in self.VALID_COLORS:
            return
        self._color = c
        self._propagate_style()

    def set_size(self, s: str):
        if s not in self.VALID_SIZES:
            return
        self._size = s
        cfg = LISTBOX_SIZES.get(s, LISTBOX_SIZES["md"])
        self._outer.setContentsMargins(
            cfg["list_padding"],
            cfg["list_padding"],
            cfg["list_padding"],
            cfg["list_padding"],
        )
        self._outer.setSpacing(cfg["group_gap"])
        self._list_v.setSpacing(cfg["list_gap"])
        self._empty_label.setMinimumHeight(cfg["empty_height"])
        self._propagate_style()

    def set_radius(self, r: str):
        if r not in RADIUS:
            return
        self._radius = r
        self._propagate_style()

    def set_hide_selected_icon(self, v: bool):
        self._hide_selected_icon = bool(v)
        self._propagate_style()

    def set_should_highlight_on_focus(self, v: bool):
        self._highlight_on_focus = bool(v)
        self._propagate_style()

    def set_disable_animation(self, v: bool):
        self._disable_animation = bool(v)
        self._propagate_style()

    # ------------------------------------------------------------
    # 样式下发
    # ------------------------------------------------------------
    def _propagate_style(self):
        cfg = LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])
        self._list_v.setSpacing(cfg["list_gap"])
        self._outer.setSpacing(cfg["group_gap"])

        selectable = self._selection_mode != "none"
        for it in self._items:
            it.apply_style(
                variant=self._variant,
                color=self._color,
                size=self._size,
                radius=self._radius,
                theme=self._theme,
                disable_animation=self._disable_animation,
                hide_selected_icon=self._hide_selected_icon,
                highlight_on_focus=self._highlight_on_focus,
                selectable=selectable,
            )
        for sec in self._sections:
            sec._apply_style(
                variant=self._variant,
                color=self._color,
                size=self._size,
                radius=self._radius,
                theme=self._theme,
                disable_animation=self._disable_animation,
                hide_selected_icon=self._hide_selected_icon,
                highlight_on_focus=self._highlight_on_focus,
                selectable=selectable,
            )

        # empty 占位主题/尺寸跟随
        self._rebuild_empty_widget()


__all__ = ["Listbox", "ListboxItem", "ListboxSection"]
