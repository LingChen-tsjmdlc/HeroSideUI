"""HeroSideUI Dropdown — 触发式下拉菜单。

复刻自 HeroUI v2 ``Dropdown``：任意 widget 当触发器，点击弹出浮层菜单，
菜单项点击后发出动作并按需关闭。
组合：trigger（默认 Button） + Popover + ScrollShadow + Listbox。

子组件：
    - ``_DropdownStylingMixin`` → ``_styling.py``
    - ``_DropdownTriggerMixin`` → ``_trigger.py``
"""

from typing import Iterable, Optional, Union

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...themes import HEROUI_COLORS, RADIUS

from ..button import Button
from ..listbox import Listbox, ListboxItem, ListboxSection
from ..popover import Popover, PopoverContent
from ..scroll_shadow import ScrollShadow
from ...utils import safe_delete

from ._styling import _DropdownStylingMixin
from ._trigger import _DropdownTriggerMixin


class Dropdown(_DropdownStylingMixin, _DropdownTriggerMixin, QWidget):
    """HeroUI 风格 Dropdown（点击触发器展开菜单）。

    用法::

        dd = Dropdown(
            trigger=Button("Actions", variant="bordered"),
            items=[
                {"key": "new", "label": "New file", "shortcut": "Ctrl+N"},
                {"key": "delete", "label": "Delete file", "color": "danger"},
            ],
        )
        dd.action.connect(lambda key: print("action:", key))
    """

    action = Signal(str)
    selection_changed = Signal(object)
    open_changed = Signal(bool)
    opened = Signal()
    closed = Signal()

    VALID_VARIANTS = ("solid", "shadow", "bordered", "flat", "faded", "light")
    VALID_COLORS = tuple(HEROUI_COLORS.keys())
    VALID_SIZES = ("sm", "md", "lg")
    VALID_RADII = tuple(k for k in RADIUS.keys() if k in ("none", "sm", "md", "lg")) + (
        "full",
    )
    VALID_SELECTION_MODES = ("none", "single", "multiple")

    @staticmethod
    def _trigger_variant(variant: str) -> str:
        """菜单变体落到 Button 触发器上；Button 没有的（如 shadow）用 solid。"""
        return variant if variant in Button.VALID_VARIANTS else "solid"

    VALID_PLACEMENTS = (
        "bottom",
        "bottom-start",
        "bottom-end",
        "top",
        "top-start",
        "top-end",
        "left",
        "left-start",
        "left-end",
        "right",
        "right-start",
        "right-end",
    )

    def __init__(
        self,
        trigger: Optional[QWidget] = None,
        items: Optional[Iterable[Union[dict, tuple, str, ListboxItem]]] = None,
        *,
        placement: str = "bottom",
        close_on_select: bool = True,
        # ---- 选中 ----
        selection_mode: str = "none",
        selected_keys: Optional[Iterable[str]] = None,
        default_selected_keys: Optional[Iterable[str]] = None,
        disabled_keys: Optional[Iterable[str]] = None,
        disallow_empty_selection: bool = False,
        # ---- 视觉 ----
        variant: str = "solid",
        color: str = "default",
        size: str = "md",
        radius: str = "md",
        shadow: str = "md",
        backdrop: str = "transparent",
        min_width: Optional[int] = None,
        max_height: Optional[int] = None,
        empty_content: Optional[str] = None,
        hide_selected_icon: bool = False,
        top_content: Optional[QWidget] = None,
        bottom_content: Optional[QWidget] = None,
        # ---- 其他 ----
        is_disabled: bool = False,
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # ---------- 参数 fallback ----------
        if placement not in self.VALID_PLACEMENTS:
            placement = "bottom"
        if variant not in self.VALID_VARIANTS:
            variant = "solid"
        if color not in self.VALID_COLORS:
            color = "default"
        if size not in self.VALID_SIZES:
            size = "md"
        if radius not in self.VALID_RADII:
            radius = "md"
        if selection_mode not in self.VALID_SELECTION_MODES:
            selection_mode = "none"

        # ---------- props ----------
        self._placement = placement
        self._close_on_select = bool(close_on_select)
        self._selection_mode = selection_mode
        self._variant = variant
        self._color = color
        self._size = size
        self._radius = radius
        self._min_width = min_width
        self._max_height = max_height
        self._hide_selected_icon = bool(hide_selected_icon)
        self._disable_animation = bool(disable_animation)
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._is_disabled = bool(is_disabled)

        # ---------- 内部状态 ----------
        initial = (
            set(selected_keys)
            if selected_keys is not None
            else set(default_selected_keys or [])
        )
        if selection_mode == "single" and len(initial) > 1:
            initial = {next(iter(initial))}
        self._selected_keys: set[str] = initial
        self._disabled_keys: set[str] = set(disabled_keys or [])
        self._item_colors: dict[str, str] = {}
        self._item_close_on_select: dict[str, bool] = {}
        self._is_open: bool = False
        self._owns_trigger: bool = False
        self._trigger_click_connected: bool = False
        self._focus_before_open: Optional[QWidget] = None

        # ---------- 外层 layout ----------
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        # ---------- Trigger ----------
        if trigger is None:
            trigger = Button(
                "Open Menu",
                variant=self._trigger_variant(variant),
                color=color,
                size=size,
                theme=theme,
                parent=self,
            )
            self._owns_trigger = True
        self._trigger = trigger
        self._outer.addWidget(trigger)

        # ---------- Popover + ScrollShadow + Listbox ----------
        self._popover = Popover(
            color="default",
            placement=placement,
            shadow=shadow,
            radius=self._popover_radius(),
            backdrop=backdrop,
            trigger_scale_on_open=False,
            disable_animation=disable_animation,
            theme=theme,
        )
        self._popover._fade._duration_in = 140
        self._popover._fade._duration_out = 100
        self._popover.attach(trigger, event="manual")

        pop_content = PopoverContent()
        pop_content.layout().setContentsMargins(0, 0, 0, 0)
        pop_content.layout().setSpacing(0)
        self._scroll = ScrollShadow(
            orientation="vertical",
            size=48,
            hide_scrollbar=True,
            theme=theme,
        )
        pop_content.layout().addWidget(self._scroll)

        self._listbox = Listbox(
            variant=variant,
            color=color,
            size=size,
            radius=radius,
            selection_mode=selection_mode,
            disabled_keys=self._disabled_keys,
            selected_keys=self._selected_keys,
            disallow_empty_selection=disallow_empty_selection,
            empty_content=empty_content,
            hide_selected_icon=hide_selected_icon,
            should_highlight_on_focus=True,
            disable_animation=disable_animation,
            top_content=top_content,
            bottom_content=bottom_content,
            theme=theme,
        )
        self._scroll.add_widget(self._listbox)
        self._listbox.action.connect(self._on_action)
        self._listbox.selection_changed.connect(self._on_selection_changed)
        self._popover.set_content(pop_content)
        self._popover.opened.connect(lambda: self._on_open_changed(True))
        self._popover.closed.connect(lambda: self._on_open_changed(False))

        # ---------- Esc 关闭（只在菜单打开时生效） ----------
        self._esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._esc.setContext(Qt.ShortcutContext.WindowShortcut)
        self._esc.activated.connect(self.close)
        self._esc.setEnabled(False)

        # ---------- Items ----------
        if items:
            self.set_items(items)

        # ---------- 事件 ----------
        self._bind_trigger()
        self._apply_disabled_state()
        self._refresh_menu_height()

        # ---------- 主题注册 ----------
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 主题
    # ============================================================
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
        self._popover.set_theme(theme)
        self._listbox.set_theme(theme)
        if hasattr(self._scroll, "set_theme"):
            self._scroll.set_theme(theme)
        if hasattr(self._trigger, "set_theme"):
            self._trigger.set_theme(theme)
        self._apply_item_color_overrides()

    # ============================================================
    # Trigger
    # ============================================================
    def trigger_widget(self) -> QWidget:
        return self._trigger

    def set_trigger(self, widget: Optional[QWidget]):
        """换触发器；旧的若为组件自建则销毁，否则仅从布局摘除。"""
        if widget is None or widget is self._trigger:
            return
        self._unbind_trigger()
        self._outer.removeWidget(self._trigger)
        old, owns = self._trigger, self._owns_trigger
        self._trigger = widget
        self._owns_trigger = False
        self._outer.addWidget(widget)
        self._popover.attach(widget, event="manual")
        self._bind_trigger()
        if owns:
            safe_delete(old)
        else:
            old.hide()
        widget.show()

    # ============================================================
    # Items 装配
    # ============================================================
    def set_items(self, items: Iterable[Union[dict, tuple, str, ListboxItem]]):
        """重置菜单项。dict 支持 label/description/shortcut/color 等字段。"""
        self._listbox.clear()
        self._item_colors.clear()
        self._item_close_on_select.clear()
        for raw in items:
            it = self._make_item(raw)
            self._listbox.add_item(it)
        self._listbox.set_disabled_keys(self._disabled_keys)
        if self._selection_mode != "none" and self._selected_keys:
            self._listbox.set_selected_keys(self._selected_keys)
        self._apply_item_color_overrides()
        self._refresh_menu_height(prefer_below=self._is_open)

    def add_item(self, item_or_title, **kwargs) -> ListboxItem:
        """追加一项；在 Listbox 参数之外额外支持 color / close_on_select。"""
        it = self._make_item(self._coerce_raw(item_or_title, kwargs))
        self._listbox.add_item(it)
        self._apply_item_color_overrides()
        self._refresh_menu_height(prefer_below=self._is_open)
        return it

    def add_section(self, title_or_section, *, show_divider: bool = False):
        """追加一个分组，返回 DropdownSection（= ListboxSection）。"""
        sec = self._listbox.add_section(title_or_section, show_divider=show_divider)
        self._refresh_menu_height(prefer_below=self._is_open)
        return sec

    def _coerce_raw(self, item_or_title, kwargs: dict):
        """把 add_item 的入参统一成 _make_item 认识的形态。"""
        if isinstance(item_or_title, (ListboxItem, tuple)):
            return item_or_title
        if isinstance(item_or_title, dict):
            return {**item_or_title, **kwargs}
        return {"label": str(item_or_title), **kwargs}

    def _make_item(self, raw) -> ListboxItem:
        if isinstance(raw, ListboxItem):
            return raw
        if isinstance(raw, dict):
            key = raw.get("key")
            color = raw.get("color")
            if color in self.VALID_COLORS and key is not None:
                self._item_colors[key] = color
            if "close_on_select" in raw and key is not None:
                self._item_close_on_select[key] = bool(raw["close_on_select"])
            return ListboxItem(
                raw.get("label", raw.get("title", "")),
                key=key,
                description=raw.get("description", ""),
                start_content=raw.get("start_content"),
                end_content=raw.get("end_content"),
                shortcut=raw.get("shortcut", ""),
                is_disabled=raw.get("is_disabled", False),
                show_divider=raw.get("show_divider", False),
            )
        if isinstance(raw, tuple) and len(raw) >= 2:
            return ListboxItem(raw[1], key=raw[0])
        return ListboxItem(str(raw), key=str(raw))

    def items(self) -> list[ListboxItem]:
        return self._listbox.items()

    def item_by_key(self, key: str) -> Optional[ListboxItem]:
        return self._listbox.item_by_key(key)

    def menu(self) -> Listbox:
        """内部菜单（Listbox）。

        增量构建建议走 ``Dropdown.add_item()`` —— 它额外支持
        ``color`` / ``close_on_select``；直接 ``menu().add_item()`` 拿不到这两项。
        """
        return self._listbox

    # ============================================================
    # 开合
    # ============================================================
    def open(self):
        if self._is_disabled or self._is_open:
            return
        self._refresh_menu_width()
        self._refresh_menu_height(prefer_below=True)
        self._popover.open(near=self._trigger)

    def close(self):
        if not self._is_open:
            return
        self._popover.close()

    def toggle(self):
        if self._is_open:
            self.close()
        else:
            self.open()

    def is_open(self) -> bool:
        return self._is_open

    def _resync_menu_height(self) -> None:
        """打开后再量一次：子项宽度要等浮层真正布局完才准。"""
        if not self._is_open:
            return
        if self._menu_target_height(True) != self._scroll.minimumHeight():
            self._refresh_menu_height(prefer_below=True)

    def _reposition_popover(self) -> None:
        """菜单高度变了重算浮层尺寸与位置（top* / *-end 方位依赖弹层高度）。"""
        pop = self._popover
        pop.adjustSize()
        pop.resize(pop.sizeHint())
        pop.move(pop._calc_position(self._trigger))

    def _on_open_changed(self, opened: bool):
        self._is_open = opened
        self._esc.setEnabled(opened)
        if opened:
            self._capture_focus()
            QTimer.singleShot(0, self, self._resync_menu_height)
        else:
            self._restore_focus()
        self.open_changed.emit(opened)
        if opened:
            self.opened.emit()
        else:
            self.closed.emit()

    def _on_action(self, key: str):
        self.action.emit(key)
        if self._should_close_on_select(key):
            self.close()

    def _should_close_on_select(self, key: str) -> bool:
        per_item = self._item_close_on_select.get(key)
        if per_item is not None:
            return per_item
        return self._close_on_select

    def _on_selection_changed(self, keys: set):
        self._selected_keys = set(keys)
        self.selection_changed.emit(self._emit_selection_payload())

    def _emit_selection_payload(self):
        """single 给 Optional[str]，multiple 给 set[str]。"""
        keys = self.selected_keys()
        if self._selection_mode == "single":
            return next(iter(keys)) if keys else None
        return set(keys)

    # ============================================================
    # 选中 / 禁用
    # ============================================================
    def selected_keys(self) -> set[str]:
        """以 Listbox 为唯一数据源，避免两侧缓存不同步。"""
        return self._listbox.selected_keys()

    def selected_key(self) -> Optional[str]:
        keys = self.selected_keys()
        return next(iter(keys)) if keys else None

    def set_selected_keys(self, keys: Iterable[str]):
        if self._selection_mode == "none":
            return
        self._selected_keys = set(keys)
        self._listbox.set_selected_keys(self._selected_keys)

    def set_selected_key(self, key: Optional[str]):
        self.set_selected_keys(set() if key is None else {key})

    def set_disabled_keys(self, keys: Iterable[str]):
        self._disabled_keys = set(keys)
        self._listbox.set_disabled_keys(self._disabled_keys)

    def set_disallow_empty_selection(self, v: bool):
        self._listbox.set_disallow_empty_selection(v)

    def set_selection_mode(self, mode: str):
        if mode not in self.VALID_SELECTION_MODES or mode == self._selection_mode:
            return
        self._selection_mode = mode
        if mode == "none":
            self._selected_keys.clear()
        self._listbox.set_selection_mode(mode)
        if mode == "single" and len(self._selected_keys) > 1:
            self._selected_keys = {next(iter(self._selected_keys))}
        if mode != "none" and self._selected_keys:
            self._listbox.set_selected_keys(self._selected_keys)
        self._apply_item_color_overrides()

    def selection_mode(self) -> str:
        return self._selection_mode

    def _apply_disabled_state(self) -> None:
        self._trigger.setEnabled(not self._is_disabled)

    def set_is_disabled(self, v: bool):
        self._is_disabled = bool(v)
        self._apply_disabled_state()
        if self._is_disabled and self._is_open:
            self.close()

    def is_disabled(self) -> bool:
        return self._is_disabled

    # ============================================================
    # 视觉 setter
    # ============================================================
    def set_variant(self, variant: str):
        if variant not in self.VALID_VARIANTS:
            return
        self._variant = variant
        self._listbox.set_variant(variant)
        if hasattr(self._trigger, "set_variant"):
            self._trigger.set_variant(self._trigger_variant(variant))
        self._apply_item_color_overrides()

    def set_color(self, color: str):
        if color not in self.VALID_COLORS:
            return
        self._color = color
        self._listbox.set_color(color)
        self._apply_item_color_overrides()

    def set_size(self, size: str):
        if size not in self.VALID_SIZES:
            return
        self._size = size
        self._listbox.set_size(size)
        if hasattr(self._trigger, "set_size"):
            self._trigger.set_size(size)
        self._apply_item_color_overrides()
        self._refresh_menu_height(prefer_below=self._is_open)

    def set_radius(self, radius: str):
        """圆角作用于浮层与菜单项；浮层不跟随 full，退化为 lg。"""
        if radius not in self.VALID_RADII:
            return
        self._radius = radius
        self._popover.set_radius(self._popover_radius())
        self._listbox.set_radius(radius)
        self._apply_item_color_overrides()

    def set_placement(self, placement: str):
        if placement not in self.VALID_PLACEMENTS:
            return
        self._placement = placement
        self._popover.set_placement(placement)

    def set_close_on_select(self, v: bool):
        self._close_on_select = bool(v)

    def set_min_width(self, w: Optional[int]):
        self._min_width = w
        if self._is_open:
            self._refresh_menu_width()

    def set_max_height(self, h: Optional[int]):
        self._max_height = h
        self._refresh_menu_height(prefer_below=self._is_open)

    def set_backdrop(self, kind: str):
        self._popover.set_backdrop(kind)

    def set_shadow(self, shadow: str):
        self._popover.set_shadow(shadow)

    def set_hide_selected_icon(self, v: bool):
        self._hide_selected_icon = bool(v)
        self._listbox.set_hide_selected_icon(v)

    def set_empty_content(self, text: Optional[str]):
        self._listbox.set_empty_content(text)

    def set_top_content(self, w: Optional[QWidget]):
        self._listbox.set_top_content(w)

    def set_bottom_content(self, w: Optional[QWidget]):
        self._listbox.set_bottom_content(w)

    def set_disable_animation(self, v: bool):
        self._disable_animation = bool(v)
        self._listbox.set_disable_animation(v)


# ============================================================
# Aliases —— 对齐 HeroUI 文档的 DropdownItem / DropdownSection
# 直接复用 ListboxItem / ListboxSection（同 Select 的做法）。
# ============================================================
DropdownItem = ListboxItem
DropdownSection = ListboxSection
