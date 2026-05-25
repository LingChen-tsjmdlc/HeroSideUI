"""HeroSideUI Select — 下拉选择框（点击触发，不可输入）。

复刻自 HeroUI v2 ``Select``，是 ``Autocomplete`` 的"降级版"——
触发钮视觉与 Input 一致，但 line_edit 强制只读，点击只切换 popover。
组合：Input（trigger） + Popover + ScrollShadow + Listbox。

子组件：
    - ``_SelectorButton``  → ``_selector_button.py``
    - ``_EndContentWidget`` → ``_end_content.py``
"""

from typing import Iterable, Optional, Union

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...themes import HEROUI_COLORS, RADIUS, SELECT_SIZES

from ..input import Input
from ..listbox import Listbox, ListboxItem, ListboxSection
from ..popover import Popover, PopoverContent
from ..scroll_shadow import ScrollShadow

from ._callbacks import _SelectCallbacksMixin
from ._end_content import _EndContentWidget
from ._styling import _SelectStylingMixin


class Select(_SelectStylingMixin, _SelectCallbacksMixin, QWidget):
    """HeroUI 风格 Select（点击展开下拉，不能输入）。

    用法::

        sel = Select(
            label="Favorite Animal",
            placeholder="Select an animal",
            items=[
                {"key": "cat", "label": "Cat"},
                {"key": "dog", "label": "Dog"},
            ],
            default_selected_keys={"cat"},
        )
        sel.selection_changed.connect(lambda keys: print("selected:", keys))
    """

    # selection_changed 在 single 时发 Optional[str]，multiple 时发 set[str]。
    selection_changed = Signal(object)
    open_changed = Signal(bool)
    closed = Signal()
    cleared = Signal()

    VALID_VARIANTS = ("flat", "faded", "bordered", "underlined")
    # 直接读 themes 全局 token，避免硬编码漂移
    VALID_COLORS = tuple(HEROUI_COLORS.keys())
    VALID_SIZES = ("sm", "md", "lg")
    VALID_RADII = tuple(k for k in RADIUS.keys() if k in ("none", "sm", "md", "lg")) + (
        "full",
    )
    VALID_LABEL_PLACEMENTS = ("inside", "outside", "outside-left", "outside-top")
    VALID_SELECTION_MODES = ("single", "multiple")

    def __init__(
        self,
        items: Optional[Iterable[Union[dict, tuple, ListboxItem]]] = None,
        *,
        # ---- 选中 ----
        selection_mode: str = "single",
        selected_keys: Optional[Iterable[str]] = None,
        default_selected_keys: Optional[Iterable[str]] = None,
        disabled_keys: Optional[Iterable[str]] = None,
        disallow_empty_selection: bool = False,
        # ---- 行为 ----
        is_clearable: bool = False,
        # ---- 视觉 ----
        selector_icon: str = "heroicons--chevron-down",
        clear_icon: str = "heroicons--x-mark-16-solid",
        disable_selector_icon_rotation: bool = False,
        empty_content: Optional[str] = None,
        placeholder: str = "Select an option",
        # ---- Input 透传 ----
        label: str = "",
        description: str = "",
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: Optional[str] = None,
        label_placement: str = "inside",
        start_content: Optional[Union[str, QWidget]] = None,
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        is_readonly: bool = False,
        # ---- Listbox 透传 ----
        listbox_variant: str = "flat",
        listbox_color: Optional[str] = None,
        # ---- 其他 ----
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # ---------- 参数 fallback ----------
        if variant not in self.VALID_VARIANTS:
            variant = "flat"
        if color not in self.VALID_COLORS:
            color = "default"
        if size not in self.VALID_SIZES:
            size = "md"
        if selection_mode not in self.VALID_SELECTION_MODES:
            selection_mode = "single"
        if listbox_variant not in (
            "solid",
            "shadow",
            "bordered",
            "flat",
            "faded",
            "light",
        ):
            listbox_variant = "flat"

        # ---------- props ----------
        self._items_data: list[dict] = []
        self._selection_mode = selection_mode
        self._disallow_empty_selection = bool(disallow_empty_selection)
        self._is_clearable = bool(is_clearable)
        self._selector_icon = selector_icon
        self._clear_icon = clear_icon
        self._disable_selector_icon_rotation = bool(disable_selector_icon_rotation)
        self._empty_content = empty_content
        self._placeholder = placeholder
        self._color = color
        self._size = size
        self._variant = variant
        self._listbox_color = (
            listbox_color if listbox_color in self.VALID_COLORS else color
        )
        self._listbox_variant = listbox_variant
        self._disable_animation = bool(disable_animation)
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._is_disabled = bool(is_disabled)
        # 用户视角的 readonly：和 Input 自身的 _is_readonly 区分（trigger
        # 内部 line_edit 永远 readOnly=True，那是为了禁用输入；这里记录
        # 用户语义的"整个 select 不可改"——readonly 时 popover 仍可打开浏览，
        # 但任何 item 都不可选。
        self._user_is_readonly = bool(is_readonly)

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
        self._is_open: bool = False
        self._is_hovered: bool = False
        # 守卫：commit 选中后关闭 popover 触发的自动 FocusIn 不应再次打开。
        self._just_committed: bool = False

        # ---------- 外层 layout ----------
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        # ---------- Trigger（复用 Input 视觉） ----------
        self._input = Input(
            label=label,
            placeholder=placeholder,
            description=description,
            variant=variant,
            color=color,
            size=size,
            radius=radius,
            label_placement=label_placement,
            value="",
            start_content=start_content,
            is_clearable=False,
            is_disabled=is_disabled,
            is_invalid=is_invalid,
            is_required=is_required,
            is_readonly=True,  # 永远 readonly：Select 不允许输入
            theme=theme,
        )
        # 让 line_edit 视觉表现为可点击按钮：手型 + 不显示文本光标
        self._input.line_edit.setReadOnly(True)
        self._input.line_edit.setCursor(Qt.PointingHandCursor)
        # contextMenu 也禁掉（粘贴/复制无意义）
        self._input.line_edit.setContextMenuPolicy(Qt.NoContextMenu)
        self._outer.addWidget(self._input)

        # ---------- end content ----------
        self._end = _EndContentWidget()
        self._refresh_end_icons()
        self._end.clear_btn.clicked.connect(self._on_clear_clicked)
        self._end.selector_btn.clicked.connect(self._on_selector_clicked)
        self._input.set_end_content(self._end)
        self._refresh_end_btn_sizes()

        # ---------- Popover + ScrollShadow + Listbox ----------
        self._popover = Popover(
            color="default",
            placement="bottom-start",
            shadow="md",
            radius="md",
            backdrop="transparent",
            trigger_scale_on_open=False,
            allow_flip=False,
            disable_animation=disable_animation,
            theme=theme,
        )
        # Select 与 Autocomplete 同属高频下拉,用更短的开关动画。
        self._popover._fade._duration_in = 140
        self._popover._fade._duration_out = 100
        self._popover.attach(self._input, event="manual")

        pop_content = PopoverContent()
        pop_content.layout().setContentsMargins(0, 0, 0, 0)
        pop_content.layout().setSpacing(0)
        self._scroll = ScrollShadow(
            orientation="vertical",
            size=48,
            hide_scrollbar=True,
            theme=theme,
        )
        cfg_sel = SELECT_SIZES.get(size, SELECT_SIZES["md"])
        self._scroll.setMaximumHeight(cfg_sel["popover_max_height"])
        self._scroll.setMinimumWidth(self._input.sizeHint().width())
        pop_content.layout().addWidget(self._scroll)

        self._listbox = Listbox(
            variant=self._listbox_variant,
            color=self._listbox_color,
            size=size,
            selection_mode=selection_mode,
            disallow_empty_selection=disallow_empty_selection,
            disable_animation=disable_animation,
            theme=theme,
            empty_content=empty_content,
            hide_selected_icon=False,
        )
        self._scroll.add_widget(self._listbox)
        self._listbox.action.connect(self._on_listbox_action)
        self._refresh_popover_height()

        self._popover.set_content(pop_content)
        self._popover.opened.connect(lambda: self._on_popover_open_changed(True))
        self._popover.closed.connect(lambda: self._on_popover_open_changed(False))

        # ---------- Items ----------
        if items:
            self.set_items(items)

        # ---------- 同步初始选中到 trigger 文本 ----------
        if self._selected_keys:
            self._listbox.set_selected_keys(self._selected_keys)
            self._seed_selected_visual()
        self._sync_trigger_text()

        # ---------- 事件过滤 ----------
        # 拦截整个 trigger 区域的点击（line_edit / wrapper 空白 / 浮动 label）
        # 都能 toggle popover；line_edit 上还顺便处理键盘导航。
        self._input.line_edit.installEventFilter(self)
        self._input._wrapper.installEventFilter(self)
        self._input._inside_label.installEventFilter(self)

        # ---------- disabled ----------
        self._apply_disabled_state()

        # ---------- 主题注册 ----------
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        self._refresh_clear_visibility()

    # ============================================================
    # 主题
    # ============================================================
    def _resolve_theme(self, mode: str) -> str:
        if mode == "auto":
            return ThemeProvider.instance().current_theme
        return mode if mode in ("light", "dark") else "light"

    def _apply_provider_theme(self, theme: str):
        if self._theme_mode != "auto":
            return
        self._theme = theme
        self._refresh_end_icons()

    def set_theme(self, theme: str):
        self._theme_mode = theme
        if theme == "auto":
            ThemeProvider.instance().register(self)
            self._theme = ThemeProvider.instance().current_theme
        elif theme in ("light", "dark"):
            self._theme = theme
        else:
            return
        self._input.set_theme(theme)
        self._listbox.set_theme(theme)
        if hasattr(self._popover, "set_theme"):
            self._popover.set_theme(theme)
        if hasattr(self._scroll, "set_theme"):
            self._scroll.set_theme(theme)
        self._refresh_end_icons()

    # ============================================================
    # Items 装配
    # ============================================================
    def set_items(self, items: Iterable[Union[dict, tuple, ListboxItem]]):
        """重置 items 列表。同 Autocomplete.set_items。"""
        self._listbox.clear()
        self._items_data.clear()
        for raw in items:
            it = self._make_item(raw)
            self._items_data.append({"key": it.key(), "label": it.title()})
            self._listbox.add_item(it)
        self._apply_disabled_state()
        if self._selected_keys:
            self._listbox.set_selected_keys(self._selected_keys)
            self._seed_selected_visual()
        self._sync_trigger_text()
        self._refresh_popover_height(prefer_below=self._is_open)

    def _make_item(self, raw) -> ListboxItem:
        if isinstance(raw, ListboxItem):
            return raw
        if isinstance(raw, dict):
            return ListboxItem(
                raw.get("label", ""),
                key=raw.get("key"),
                description=raw.get("description", ""),
                start_content=raw.get("start_content"),
                end_content=raw.get("end_content"),
                shortcut=raw.get("shortcut", ""),
                is_disabled=raw.get("is_disabled", False),
                show_divider=raw.get("show_divider", False),
            )
        if isinstance(raw, tuple) and len(raw) >= 2:
            key, label = raw[0], raw[1]
            return ListboxItem(label, key=key)
        return ListboxItem(str(raw), key=str(raw))

    def items(self) -> list[ListboxItem]:
        return self._listbox.items()

    def item_by_key(self, key: str) -> Optional[ListboxItem]:
        return self._listbox.item_by_key(key)

    # ============================================================
    # 公共 getter / setter
    # ============================================================
    def selected_keys(self) -> set[str]:
        return set(self._selected_keys)

    def selected_key(self) -> Optional[str]:
        """single 模式专用：返回当前选中 key 或 None。"""
        if not self._selected_keys:
            return None
        return next(iter(self._selected_keys))

    def set_selected_keys(self, keys: Iterable[str]):
        new_keys = set(keys)
        if self._selection_mode == "single" and len(new_keys) > 1:
            new_keys = {next(iter(new_keys))}
        # 必选语义：空集请求被拒（保持当前选中）
        if self._disallow_empty_selection and not new_keys and self._selected_keys:
            return
        if new_keys == self._selected_keys:
            return
        self._selected_keys = new_keys
        self._listbox.set_selected_keys(new_keys)
        self._sync_trigger_text()
        self._refresh_clear_visibility()
        self.selection_changed.emit(self._emit_selection_payload())

    def set_selected_key(self, key: Optional[str]):
        """single 模式便捷 setter。"""
        self.set_selected_keys(set() if key is None else {key})

    def is_open(self) -> bool:
        return self._is_open

    def selection_mode(self) -> str:
        return self._selection_mode

    # ============================================================
    # Popover 高度刷新
    # ============================================================
    def _popover_max_height(self) -> int:
        cfg = SELECT_SIZES.get(self._size, SELECT_SIZES["md"])
        return int(cfg["popover_max_height"])

    def _available_scroll_height_below(self) -> int:
        screen = QApplication.primaryScreen()
        if screen is None:
            return self._popover_max_height()
        rect = screen.availableGeometry()
        pos = self._input.mapToGlobal(QPoint(0, 0))
        gap = 6
        _, _, _, bottom_margin = self._popover._frame_margins()
        return int(
            rect.bottom() - (pos.y() + self._input.height()) - gap - bottom_margin
        )

    def _visible_listbox_content_height(self) -> int:
        """同 Autocomplete.同名方法。"""
        try:
            cfg_outer = self._listbox._outer.contentsMargins()
            gap = self._listbox._list_v.spacing()
            visible_widgets = [
                self._listbox._list_v.itemAt(i).widget()
                for i in range(self._listbox._list_v.count())
            ]
            visible_widgets = [
                w for w in visible_widgets if w is not None and not w.isHidden()
            ]
            if not visible_widgets:
                visible_widgets = [self._listbox._empty_widget]
            h = sum(w.sizeHint().height() for w in visible_widgets)
            h += max(0, len(visible_widgets) - 1) * max(0, gap)
            h += cfg_outer.top() + cfg_outer.bottom()
            return int(h)
        except Exception:
            return int(self._listbox.sizeHint().height())

    def _refresh_popover_height(self, prefer_below: bool = False) -> None:
        token_max = self._popover_max_height()
        max_h = token_max
        if prefer_below:
            max_h = min(max_h, self._available_scroll_height_below())
        max_h = min(token_max, max(80, int(max_h)))

        content_h = max(1, self._visible_listbox_content_height())
        old_cap = max(80, token_max // 2)
        if content_h > old_cap:
            target = max_h
        else:
            target = min(content_h, max_h)
            target = max(80, int(target))

        self._scroll.setMinimumHeight(target)
        self._scroll.setMaximumHeight(max_h)
        self._scroll.updateGeometry()

    # ============================================================
    # Popover 控制
    # ============================================================
    def open(self):
        if self._is_disabled or self._is_open:
            return
        w = max(self._input.width(), self._input.sizeHint().width())
        self._scroll.setMinimumWidth(w)
        self._scroll.setMaximumWidth(w)
        self._refresh_popover_height(prefer_below=True)
        self._popover.open(near=self._input)

    def close(self):
        if not self._is_open:
            return
        self._popover.close()

    def toggle(self):
        if self._is_open:
            self.close()
        else:
            self.open()

    # ============================================================
    # Trigger 文本同步
    # ============================================================
    def _selected_labels(self) -> list[str]:
        """按 items 出现顺序返回当前选中项的 label，缺失项跳过。"""
        labels = []
        for it in self._listbox.items():
            if it.key() in self._selected_keys:
                labels.append(it.title())
        return labels

    def _sync_trigger_text(self):
        labels = self._selected_labels()
        if not labels:
            text = ""
        elif self._selection_mode == "single":
            text = labels[0]
        else:
            # multiple：逗号分隔；超过 chip_max 显示 +N
            cfg = SELECT_SIZES.get(self._size, SELECT_SIZES["md"])
            cap = int(cfg.get("chip_max", 3))
            if len(labels) <= cap:
                text = ", ".join(labels)
            else:
                text = ", ".join(labels[:cap]) + f", +{len(labels) - cap}"
        self._input.set_text(text)
        # 兜底刷一次浮动 label 与 filled 状态，避免 setText 在某些 reentrancy
        # 场景下 textChanged 没把 label 归位（取消最后一个勾选时高发）
        self._input._update_filled_state()
        self._input._update_label_animation()

    def _emit_selection_payload(self):
        """selection_changed 发出的 payload：single 给 Optional[str]，
        multiple 给 set[str]。"""
        if self._selection_mode == "single":
            return next(iter(self._selected_keys)) if self._selected_keys else None
        return set(self._selected_keys)

    # ============================================================
    # 透传 setter
    # ============================================================
    def set_label(self, label: str):
        self._input.set_label(label)

    def set_placeholder(self, placeholder: str):
        self._placeholder = placeholder
        self._input.set_placeholder(placeholder)

    def set_description(self, description: str):
        self._input.set_description(description)

    def set_variant(self, variant: str):
        if variant not in self.VALID_VARIANTS:
            return
        self._variant = variant
        self._input.set_variant(variant)

    def set_color(self, color: str):
        if color not in self.VALID_COLORS:
            return
        self._color = color
        self._input.set_color(color)
        if self._listbox_color == self._color:
            self._listbox.set_color(color)
        self._refresh_end_icons()

    def set_size(self, size: str):
        if size not in self.VALID_SIZES:
            return
        self._size = size
        self._input.set_size(size)
        self._listbox.set_size(size)
        self._refresh_popover_height(prefer_below=self._is_open)
        self._refresh_end_btn_sizes()
        self._refresh_end_icons()
        self._sync_trigger_text()

    def set_radius(self, radius: Optional[str]):
        if radius is not None and radius not in self.VALID_RADII:
            return
        self._input.set_radius(radius)

    def set_label_placement(self, p: str):
        self._input.set_label_placement(p)

    def set_is_disabled(self, v: bool):
        self._is_disabled = bool(v)
        self._input.set_is_disabled(v)
        if self._is_disabled and self._is_open:
            self.close()

    def set_is_invalid(self, v: bool):
        self._input.set_is_invalid(v)

    def set_is_required(self, v: bool):
        self._input.set_is_required(v)

    def set_is_readonly(self, v: bool):
        self._user_is_readonly = bool(v)
        self._apply_disabled_state()

    def set_is_clearable(self, v: bool):
        self._is_clearable = bool(v)
        self._refresh_clear_visibility()

    def set_disallow_empty_selection(self, v: bool):
        self._disallow_empty_selection = bool(v)
        self._listbox.set_disallow_empty_selection(self._disallow_empty_selection)
        self._refresh_clear_visibility()

    def set_disabled_keys(self, keys: Iterable[str]):
        self._disabled_keys = set(keys)
        self._apply_disabled_state()

    def _apply_disabled_state(self) -> None:
        """统一计算并下发 listbox disabled keys。

        readonly=True 时整表禁选（对齐 HeroUI 语义）。
        """
        if self._user_is_readonly:
            all_keys = {it.key() for it in self._listbox.items()}
            effective = self._disabled_keys | all_keys
        else:
            effective = set(self._disabled_keys)
        self._listbox.set_disabled_keys(effective)

    def _seed_selected_visual(self) -> None:
        # 构造期 / set_items 后 listbox 还没显示，set_selected 走的 tween + delay
        # 启动的描勾动画，在首次打开 popover 前若没及时跑到 progress=1 / alpha=1，
        # 用户会看到"trigger 已显示选中文本，但下拉里没√"。这里把已选 item 直接
        # 推到稳定终态，跳过动画。
        for it in self._listbox.items():
            if it.key() in self._selected_keys:
                it._check_anim.set_immediate(True)
                it._cur_indicator_alpha = 1.0
                it.update()

    def set_empty_content(self, text: Optional[str]):
        self._empty_content = text
        self._listbox.set_empty_content(text)

    # ------------------------------------------------------------
    # 宽度透传 —— Select 外壳是垂直 layout 套 Input，外壳设宽不会
    # 压过 Input 的 min_width 守卫（默认 260），导致 Input 撑出 Select
    # 边界、chevron 被裁。统一把宽度调用转发给 Input
    def setFixedWidth(self, w: int):  # noqa: N802
        self._input.setFixedWidth(int(w))
        super().setFixedWidth(int(w))

    def setMinimumWidth(self, w: int):  # noqa: N802
        self._input.setMinimumWidth(int(w))
        super().setMinimumWidth(int(w))

    def setMaximumWidth(self, w: int):  # noqa: N802
        self._input.setMaximumWidth(int(w))
        super().setMaximumWidth(int(w))

    def set_disable_selector_icon_rotation(self, v: bool):
        self._disable_selector_icon_rotation = bool(v)
        if v:
            self._end.selector_btn.set_angle(0, animated=False)
        else:
            target = 180.0 if self._is_open else 0.0
            self._end.selector_btn.set_angle(target, animated=False)

    def set_selection_mode(self, mode: str):
        if mode not in self.VALID_SELECTION_MODES or mode == self._selection_mode:
            return
        self._selection_mode = mode
        self._listbox.set_selection_mode(mode)
        # 切到 single 时收敛多选
        if mode == "single" and len(self._selected_keys) > 1:
            keep = next(iter(self._selected_keys))
            self._selected_keys = {keep}
            self._listbox.set_selected_keys(self._selected_keys)
        self._sync_trigger_text()

    # ============================================================
    # Trigger 事件过滤：点击 / 键盘
    # ============================================================
    def eventFilter(self, obj, event):
        # ---- 鼠标点击：trigger 内任意位置（line_edit / wrapper / 浮动 label）
        # 都能 toggle popover ----
        if obj in (
            self._input.line_edit,
            self._input._wrapper,
            self._input._inside_label,
        ):
            if event.type() == QEvent.MouseButtonRelease:
                if not self._is_disabled and event.button() == Qt.LeftButton:
                    if self._just_committed:
                        # 守卫期：刚 commit 关闭 popover 后的同一帧点击吞掉
                        return True
                    self.toggle()
                    return True

        # ---- 键盘事件：只在 line_edit 持有焦点时处理 ----
        if obj is self._input.line_edit and event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Down, Qt.Key_Up):
                if not self._is_open:
                    self.open()
                    idx = self._listbox._first_enabled_index()
                    if idx >= 0:
                        self._listbox._set_focus_index(idx)
                else:
                    self._listbox._move_focus(1 if key == Qt.Key_Down else -1)
                return True
            if key == Qt.Key_Home and self._is_open:
                idx = self._listbox._first_enabled_index()
                if idx >= 0:
                    self._listbox._set_focus_index(idx)
                return True
            if key == Qt.Key_End and self._is_open:
                idx = self._listbox._last_enabled_index()
                if idx >= 0:
                    self._listbox._set_focus_index(idx)
                return True
            if key == Qt.Key_Escape and self._is_open:
                self.close()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                if not self._is_open:
                    self.open()
                    return True
                idx = self._listbox._focused_index
                if 0 <= idx < len(self._listbox._items):
                    it = self._listbox._items[idx]
                    if not it.is_disabled():
                        self._listbox._on_item_activated(it.key())
                return True

        return super().eventFilter(obj, event)


# ============================================================
# Aliases —— 对齐 HeroUI 文档的 SelectItem / SelectSection
# 直接复用 ListboxItem / ListboxSection（HeroUI 文档原话亦如此）。
# ============================================================
SelectItem = ListboxItem
SelectSection = ListboxSection
