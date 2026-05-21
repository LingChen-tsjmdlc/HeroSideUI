"""
HeroSideUI Listbox Component — 主容器
=====================================
基于 HeroUI v2 的 menu/listbox 设计风格。

样式来源：
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/menu.ts
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/listbox.ts
    https://github.com/heroui-inc/heroui/tree/main/packages/components/listbox

结构::

    Listbox (QWidget)            ← 本文件
        ├── topContent     (可选)
        ├── _list_container (QWidget, list slot)
        │     ├── ListboxItem / ListboxSection ...
        │     └── _empty_label (默认隐藏)
        └── bottomContent  (可选)

子组件：
    - ``ListboxItem``  → ``item.py``
    - ``ListboxSection`` → ``section.py``

特性对齐 HeroUI:
    - 6 variants: solid / shadow / bordered / flat / faded / light
    - 6 colors:   default / primary / secondary / success / warning / danger
    - 3 sizes:    sm / md / lg
    - selection_mode: none / single / multiple
    - showDivider / isDisabled / disable_animation
    - hide_selected_icon / should_highlight_on_focus
    - 信号: selection_changed(set[str]) / action(str)
    - 主题: light / dark / auto
"""

from __future__ import annotations

from typing import Iterable, Optional, Union

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import (
    CheckDrawAnimation,
    paint_animated_check,
    stop_tween,
    tween_value,
)
from ...core import StatePalette, ThemeProvider
from ...themes import HEROUI_COLORS, LISTBOX_SIZES, RADIUS
from ...utils import aligned_color_pair, load_svg_icon

from ..text import Text
from .item import ListboxItem
from .section import ListboxSection

# ============================================================
# Listbox
# ============================================================


class Listbox(QWidget):
    """HeroUI 风格列表框。

    用法::

        lb = Listbox(variant="flat", color="primary", selection_mode="single")
        lb.add_item("New", key="new", description="Create a new file", shortcut="Ctrl+N")
        lb.add_item("Copy", key="copy")
        lb.add_item("Paste", key="paste")
        lb.action.connect(lambda key: print("activated", key))
        lb.selection_changed.connect(lambda keys: print("selected", keys))

    分组::

        sec = ListboxSection("Actions", show_divider=True)
        sec.add_item("Copy", key="copy")
        lb.add_section(sec)
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
        self._hide_selected_icon = hide_selected_icon
        self._highlight_on_focus = should_highlight_on_focus
        self._disable_animation = disable_animation
        self._is_disabled = is_disabled
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # 选中/禁用 key 状态
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

        # topContent
        self._top_content: Optional[QWidget] = None
        if top_content is not None:
            self.set_top_content(top_content)

        # list 容器（list slot）
        self._list = QWidget(self)
        self._list.setAttribute(Qt.WA_TranslucentBackground, True)
        self._list_v = QVBoxLayout(self._list)
        self._list_v.setContentsMargins(0, 0, 0, 0)
        self._list_v.setSpacing(cfg["list_gap"])
        self._outer.addWidget(self._list)

        # emptyContent
        # 用户传 str → 单行文字（兼容旧用法）
        # 用户传 None（默认）→ 居中 icon + 中英双语 ("Nothing to show / 暂无内容")
        self._empty_content_text = empty_content  # None / "" 都视为用默认 icon 模式
        self._empty_widget: QWidget = (
            QWidget()
        )  # 占位，立刻被 _rebuild_empty_widget 替换
        self._list_v.addWidget(self._empty_widget)
        self._empty_label: "Text" = Text("")  # 占位，立刻被 _rebuild_empty_widget 替换
        self._rebuild_empty_widget()
        self._empty_widget.hide()
        # 末尾 stretch:让 items 在父容器(如 popover)给的高度大于 items 实际总高度时
        # 顶部对齐,不被 QVBoxLayout 默认拉伸成"垂直居中的大块"。
        # 必须始终保持在 list_v 最末尾 —— add_item / add_section 后都要 _ensure_trailing_stretch()。
        self._list_v.addStretch(1)

        # bottomContent
        self._bottom_content: Optional[QWidget] = None
        if bottom_content is not None:
            self.set_bottom_content(bottom_content)

        # 子项 / 分组
        self._items: list[ListboxItem] = []
        self._sections: list[ListboxSection] = []

        # 焦点项索引（键盘导航用）
        self._focused_index = -1

        self.setFocusPolicy(Qt.StrongFocus)

        # 注册主题
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
        # _empty_widget 内部的 icon pixmap + 文字 stylesheet 是构造时 cache 的,
        # 主题切换时不会自己刷新,必须显式重建一遍。否则 dark 模式下 icon/文字
        # 还是 light 模式的色号,看起来"消失"。
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
    # 公共 API：装配
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
        """追加一项。

        - 传 ``ListboxItem`` 实例 → 直接挂上
        - 传 ``str`` (title) + 关键字参数 → 内部构造 ``ListboxItem``
        """
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
        # 插到 _empty_widget 之前(_empty_widget 才是 list_v 的直接子项,
        # _empty_label 是 _empty_widget 内部的 QLabel,indexOf 永远是 -1)。
        # 这样保证末尾的 stretch 永远在最后,items 顶部对齐不被拉伸。
        idx = self._list_v.indexOf(self._empty_widget)
        if idx < 0:
            self._list_v.insertWidget(
                self._list_v.count() - 1, it
            )  # 倒数第二位(stretch 之前)
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
        # 把分组里现有 item 都注册到 _items 列表（用于键盘导航 / disabled 同步）
        for it in sec.items():
            self._attach_item(it)
            self._items.append(it)

        idx = self._list_v.indexOf(self._empty_widget)
        if idx < 0:
            self._list_v.insertWidget(self._list_v.count() - 1, sec)  # stretch 之前
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
        """所有可交互项（包含 section 内）"""
        return list(self._items)

    def item_by_key(self, key: str) -> Optional[ListboxItem]:
        for it in self._items:
            if it.key() == key:
                return it
        return None

    def _attach_item(self, it: ListboxItem):
        # 同步 disabled key
        if it.key() in self._disabled_keys:
            it.set_disabled(True)
        # 同步选中 key
        if it.key() in self._selected_keys and self._selection_mode != "none":
            it.set_selected(True)
        # 监听点击/选中
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
            # 清空选中
            self._selected_keys.clear()
            for it in self._items:
                it.set_selected(False)
        self._propagate_style()

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
        # 通过 opacity effect 一刀切（不动 enabled，键盘焦点保留语义）
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

    def set_empty_content(self, text: Optional[str]):
        """设置空状态文案。

        - 传 ``None`` / ``""``：恢复默认（icon + 中英双语）
        - 传非空 ``str``：单行文字
        """
        self._empty_content_text = text
        self._rebuild_empty_widget()

    def _rebuild_empty_widget(self):
        """重建 empty 占位 widget —— 在 set_empty_content / size / theme 变化时调用。"""
        idx = self._list_v.indexOf(self._empty_widget)
        # 用 isHidden() 而不是 isVisible():isVisible 在 parent (popover) 不可见时
        # 即使我们 setVisible(True) 也会返回 False —— 主题切换时 popover 关闭 +
        # listbox 隐藏,被骗到这里 was_visible=False,新 empty_widget 跟着 hide,
        # 下次 popover 打开 empty 内容还是缺,要用户再触发一次 _apply_filter 才出现。
        # 用 isHidden() 看的是 widget 自己 explicit 的 visible flag,不受 parent 影响。
        was_visible = not self._empty_widget.isHidden()
        self._list_v.removeWidget(self._empty_widget)
        self._empty_widget.setParent(None)
        self._empty_widget.deleteLater()
        self._empty_widget = self._build_empty_widget()
        cfg = LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])
        # 默认模式（icon + 双语）需要更高的占位空间；自定义文字保持原 empty_height
        if self._empty_content_text:
            self._empty_widget.setMinimumHeight(cfg["empty_height"])
        else:
            # icon (3×title) + 两行文字 + 上下 padding + spacing
            self._empty_widget.setMinimumHeight(
                cfg["title_font_size"] * 3
                + cfg["title_font_size"]
                + cfg["desc_font_size"]
                + cfg["item_padding_y"] * 4
                + 16
            )
        if idx < 0:
            self._list_v.addWidget(self._empty_widget)
        else:
            self._list_v.insertWidget(idx, self._empty_widget)
        self._empty_label = self._empty_widget.findChild(
            QLabel, "heroEmptyText"
        ) or Text("")
        self._empty_widget.setVisible(was_visible)

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
    # 内部
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

        # empty 占位主题/尺寸跟随：直接重建 widget（icon 颜色 / 字号都依赖 theme + size）
        self._rebuild_empty_widget()

    def _refresh_empty(self):
        # 如果完全没 item（独立 + section 内部），显示 empty 占位（icon + 双语 / 自定义文字）
        empty = len(self._items) == 0
        self._empty_widget.setVisible(empty)

    def _build_empty_widget(self) -> QWidget:
        """构造空状态占位 widget。

        - ``_empty_content_text`` 为 None 或空：默认模式 → 居中 icon + 中英双语
        - 非空 str：单行文字（保持原行为兼容）
        """
        from PySide6.QtWidgets import QSizePolicy
        from PySide6.QtCore import Qt

        cfg = LISTBOX_SIZES.get(self._size, LISTBOX_SIZES["md"])
        w = QWidget(self._list)
        w.setAttribute(Qt.WA_TranslucentBackground, True)

        if self._empty_content_text:
            # 兼容模式：单行文字
            v = QVBoxLayout(w)
            v.setContentsMargins(
                cfg["item_padding_x"],
                cfg["item_padding_y"],
                cfg["item_padding_x"],
                cfg["item_padding_y"],
            )
            v.setSpacing(0)
            text_label = Text(
                self._empty_content_text,
                parent=w,
                color=StatePalette.text_description(self._theme).name(),
                selectable=False,
            )
            text_label.setObjectName("heroEmptyText")
            text_label.setAttribute(Qt.WA_TranslucentBackground, True)
            text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            v.addWidget(text_label)
            return w

        # 默认模式：icon + 中英双语
        v = QVBoxLayout(w)
        v.setContentsMargins(
            cfg["item_padding_x"],
            cfg["item_padding_y"] * 2,
            cfg["item_padding_x"],
            cfg["item_padding_y"] * 2,
        )
        v.setSpacing(8)
        v.setAlignment(Qt.AlignCenter)

        # icon
        icon_size = cfg["title_font_size"] * 3  # md=42, sm=36, lg=45 视觉适中
        icon_color = StatePalette.text_description(self._theme)
        icon_label = QLabel(w)
        icon_label.setObjectName("heroEmptyIcon")
        icon_label.setAttribute(Qt.WA_TranslucentBackground, True)
        icon_label.setAlignment(Qt.AlignCenter)
        pix = load_svg_icon(
            "mingcute--empty-box-line", size=icon_size, color=icon_color
        )
        icon_label.setPixmap(pix)
        icon_label.setFixedSize(icon_size, icon_size)
        v.addWidget(icon_label, 0, Qt.AlignCenter)

        # 双语文字（en 在上，cn 在下，cn 字号略小）
        en_label = Text(
            "Nothing to show",
            parent=w,
            size=cfg["title_font_size"],
            color=StatePalette.text_description(self._theme).name(),
            selectable=False,
        )
        en_label.setObjectName("heroEmptyText")  # 主文本对外暴露给 _empty_label
        en_label.setAttribute(Qt.WA_TranslucentBackground, True)
        en_label.setAlignment(Qt.AlignCenter)
        v.addWidget(en_label, 0, Qt.AlignCenter)

        cn_label = Text(
            "暂无内容",
            parent=w,
            size=cfg["desc_font_size"],
            color=StatePalette.text_description(self._theme).name(),
            selectable=False,
        )
        cn_label.setObjectName("heroEmptyTextCn")
        cn_label.setAttribute(Qt.WA_TranslucentBackground, True)
        cn_label.setAlignment(Qt.AlignCenter)
        v.addWidget(cn_label, 0, Qt.AlignCenter)

        return w

    def _on_item_activated(self, key: str):
        # 选中态切换
        if self._selection_mode == "single":
            old = set(self._selected_keys)
            if key in self._selected_keys:
                # 单选模式下点击已选项 —— HeroUI 默认仍保持选中（disallowEmptySelection），
                # 我们对齐：保持选中
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

        # action 总是在每次点击触发
        self.action.emit(key)

    # ------------------------------------------------------------
    # 键盘导航
    # ------------------------------------------------------------
    def keyPressEvent(self, e):
        key = e.key()
        if key in (Qt.Key_Down, Qt.Key_Up):
            step = 1 if key == Qt.Key_Down else -1
            self._move_focus(step)
            e.accept()
            return
        if key == Qt.Key_Home:
            self._set_focus_index(self._first_enabled_index())
            e.accept()
            return
        if key == Qt.Key_End:
            self._set_focus_index(self._last_enabled_index())
            e.accept()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if 0 <= self._focused_index < len(self._items):
                it = self._items[self._focused_index]
                if not it.is_disabled():
                    it.activated.emit(it.key())
                    self._on_item_activated(it.key())
            e.accept()
            return
        super().keyPressEvent(e)

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


__all__ = ["Listbox", "ListboxItem", "ListboxSection"]
