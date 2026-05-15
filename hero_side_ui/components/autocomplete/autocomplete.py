"""HeroSideUI Autocomplete — 自动完成/搜索下拉框。

组合：Input（顶部触发） + Popover（浮层容器） + Listbox（选项列表）。

子组件：
    - ``_SelectorButton``  → ``_selector_button.py``
    - ``_EndContentWidget`` → ``_end_content.py``
"""

from typing import Callable, Iterable, List, Optional, Union

from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import stop_tween, tween_value
from ...core import ThemeProvider
from ...themes import (
    AUTOCOMPLETE_SIZES,
    FONT_FAMILY,
    HEROUI_COLORS,
    INPUT_SIZES,
    RADIUS,
)
from ...utils import load_svg_icon

from ..button import Button
from ..input import Input
from ..listbox import Listbox, ListboxItem, ListboxSection
from ..popover import Popover, PopoverContent
from ..scroll_shadow import ScrollShadow

from ._callbacks import _AutocompleteCallbacksMixin
from ._end_content import _EndContentWidget
from ._keyboard import _AutocompleteKeyboardMixin
from ._selector_button import _SelectorButton
from ._styling import _AutocompleteStylingMixin


def _default_contains_filter(item_label: str, query: str) -> bool:
    if not query:
        return True
    return query.lower() in item_label.lower()


# ============================================================
# Autocomplete
# ============================================================
class Autocomplete(
    _AutocompleteStylingMixin,
    _AutocompleteCallbacksMixin,
    _AutocompleteKeyboardMixin,
    QWidget,
):
    """HeroUI 风格 Autocomplete（输入即过滤的下拉补全框）。

    用法::

        ac = Autocomplete(
            label="Favorite Animal",
            placeholder="Type to search...",
            items=[
                {"key": "cat", "label": "Cat", "description": "Domestic feline"},
                {"key": "dog", "label": "Dog"},
                {"key": "elephant", "label": "Elephant"},
            ],
            default_selected_key="cat",
        )
        ac.selection_changed.connect(lambda k: print("selected:", k))
        ac.input_changed.connect(lambda t: print("typing:", t))
    """

    selection_changed = Signal(object)  # str | None
    input_changed = Signal(str)
    open_changed = Signal(bool, str)  # (open, menu_trigger)
    cleared = Signal()
    submitted = Signal(str)  # Enter + allows_custom_value 时发当前 input text

    VALID_VARIANTS = ("flat", "faded", "bordered", "underlined")
    VALID_COLORS = ("default", "primary", "secondary", "success", "warning", "danger")
    VALID_SIZES = ("sm", "md", "lg")
    VALID_LABEL_PLACEMENTS = ("inside", "outside", "outside-left", "outside-top")
    VALID_MENU_TRIGGERS = ("focus", "input", "manual")

    def __init__(
        self,
        # ---- core ----
        items: Optional[Iterable[Union[dict, tuple, ListboxItem]]] = None,
        *,
        # ---- text / selection state ----
        input_value: Optional[str] = None,
        default_input_value: Optional[str] = None,
        selected_key: Optional[str] = None,
        default_selected_key: Optional[str] = None,
        disabled_keys: Optional[Iterable[str]] = None,
        # ---- 行为 ----
        default_filter: Optional[Callable[[str, str], bool]] = None,
        allows_custom_value: bool = False,
        is_clearable: bool = True,
        menu_trigger: str = "focus",
        # ---- 视觉 ----
        selector_icon: str = "heroicons--chevron-down",
        clear_icon: str = "heroicons--x-mark-16-solid",
        disable_selector_icon_rotation: bool = False,
        empty_content: Optional[str] = None,
        # ---- Input 透传 ----
        label: str = "",
        placeholder: str = "",
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
        # ---- Listbox 透传（可选 override） ----
        listbox_variant: str = "flat",
        listbox_color: Optional[str] = None,  # None → 跟随 color
        # ---- 其他 ----
        disable_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # 参数校验 / fallback
        if variant not in self.VALID_VARIANTS:
            variant = "flat"
        if color not in self.VALID_COLORS:
            color = "default"
        if size not in self.VALID_SIZES:
            size = "md"
        if menu_trigger not in self.VALID_MENU_TRIGGERS:
            menu_trigger = "focus"
        if listbox_variant not in (
            "solid",
            "shadow",
            "bordered",
            "flat",
            "faded",
            "light",
        ):
            listbox_variant = "flat"

        # ---------- 保存 props ----------
        self._items_data: list[dict] = []  # 后面 set_items 填充
        self._filter = default_filter or _default_contains_filter
        self._allows_custom_value = bool(allows_custom_value)
        self._is_clearable = bool(is_clearable)
        self._menu_trigger = menu_trigger
        self._selector_icon = selector_icon
        self._clear_icon = clear_icon
        self._disable_selector_icon_rotation = bool(disable_selector_icon_rotation)
        self._empty_content = empty_content
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

        # ---------- 内部状态 ----------
        # selected_key / input_value 受控 vs 非受控：HeroUI 同时支持，
        # 这里以 default_xxx 初始化内部状态；选中变化时同时发信号给用户。
        self._selected_key: Optional[str] = (
            selected_key if selected_key is not None else default_selected_key
        )
        initial_text = (
            input_value if input_value is not None else (default_input_value or "")
        )
        self._input_value: str = initial_text
        self._is_open: bool = False
        self._disabled_keys: set[str] = set(disabled_keys or [])

        # 防递归：set_text 触发 textChanged 又触发 _on_input_changed 的循环
        self._programmatic_text = False
        # 守卫：commit 选中后短时间内禁止 FocusIn 自动重开 popover。
        # Qt Tool/Popup 窗口关闭时会把焦点还给"上一个聚焦 widget"（line_edit），
        # 触发 FocusIn → menu_trigger="focus" 命中 → 又调 open() → 用户感受到
        # "popover 先消失又自动出现"。窗口设为 popover 关闭动画时长 + 余量。
        self._just_committed = False
        # hover 状态:hover 才显示 clear 按钮(对齐 HeroUI 视觉行为)。
        # 鼠标进/出由 enterEvent/leaveEvent 维护,不依赖 QSS :hover ——
        # QSS :hover 改不了子 widget 的 visibility,必须 Python 接管。
        self._is_hovered: bool = False

        # ---------- 外层 layout ----------
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        # ---------- Input ----------
        self._input = Input(
            label=label,
            placeholder=placeholder,
            description=description,
            variant=variant,
            color=color,
            size=size,
            radius=radius,
            label_placement=label_placement,
            value=self._input_value,
            start_content=start_content,
            is_clearable=False,  # 自己接管 clear
            is_disabled=is_disabled,
            is_invalid=is_invalid,
            is_required=is_required,
            is_readonly=is_readonly,
            theme=theme,
        )
        self._outer.addWidget(self._input)

        # ---------- end content (clear + selector) ----------
        self._end = _EndContentWidget()
        self._refresh_end_icons()
        self._end.clear_btn.clicked.connect(self._on_clear_clicked)
        self._end.selector_btn.clicked.connect(self._on_selector_clicked)
        self._input.set_end_content(self._end)
        self._refresh_end_btn_sizes()

        # ---------- Popover + ScrollShadow + Listbox ----------
        self._popover = Popover(
            color="default",  # popover 背景跟随主题，不带色（避免和 listbox 着色冲突）
            placement="bottom-start",
            shadow="md",
            radius="md",
            backdrop="transparent",
            trigger_scale_on_open=False,
            allow_flip=False,  # Combobox/Autocomplete 下拉框必须优先向下，空间不够时由内部滚动承接
            disable_animation=disable_animation,
            theme=theme,
        )
        # Autocomplete 的 popover 节奏要快——下拉框是高频交互组件，默认 280/200
        # 偏长，缩成 140/100（in 减半、out 减半），更接近 native combobox 体感。
        self._popover._fade._duration_in = 140
        self._popover._fade._duration_out = 100
        # 注:popover 在自定义插槽场景(Autocomplete/Select 等复合组件)只走 fade,
        # 不再做 padding squeeze——已在 Popover.open()/close() 中按
        # `_content_is_text_only` 分支控制。这里不需要再覆盖 squeeze 参数。
        self._popover.attach(self._input, event="manual")

        # popover 内容：ScrollShadow + Listbox
        pop_content = PopoverContent()
        # popover padding 默认 10，我们这里缩到 0（listbox 自带 p-1）
        pop_content.layout().setContentsMargins(0, 0, 0, 0)
        pop_content.layout().setSpacing(0)
        # ScrollShadow:
        # - hide_scrollbar=True：HeroUI 原版不显示滚动条，靠渐变阴影暗示可滚
        # - fade_color 不显式传：ScrollShadow 内部会沿 parent 链找 popover 的
        #   ``current_bg_color()`` 方法（duck typing），自动取到 popover 实际底色
        #   做渐变终点，保证主题/颜色切换都跟得上（MEMORY 第 32 条范式）
        self._scroll = ScrollShadow(
            orientation="vertical",
            size=48,
            hide_scrollbar=True,
            theme=theme,
        )
        # 高度上限：popover_max_height。注意 QScrollArea 的 sizeHint 不会因为
        # setMaximumHeight 自动变大，实际弹层高度由 _refresh_popover_height()
        # 按 listbox 内容高度和屏幕下方可用空间计算后 setFixedHeight。
        cfg_ac = AUTOCOMPLETE_SIZES.get(size, AUTOCOMPLETE_SIZES["md"])
        self._scroll.setMaximumHeight(cfg_ac["popover_max_height"])
        self._scroll.setMinimumWidth(self._input.sizeHint().width())
        pop_content.layout().addWidget(self._scroll)

        self._listbox = Listbox(
            variant=self._listbox_variant,
            color=self._listbox_color,
            size=size,
            selection_mode="single",
            disable_animation=disable_animation,
            theme=theme,
            empty_content=empty_content,  # None → listbox 默认 icon + 双语
            hide_selected_icon=False,  # 对齐 HeroUI: 已选项右侧显示对勾标记
        )
        self._scroll.add_widget(self._listbox)
        # 监听 listbox 行为
        self._listbox.action.connect(self._on_listbox_action)
        self._refresh_popover_height()

        self._popover.set_content(pop_content)
        self._popover.opened.connect(
            lambda: self._on_popover_open_changed(
                True, getattr(self, "_pending_trigger", "manual")
            )
        )
        self._popover.closed.connect(
            lambda: self._on_popover_open_changed(False, "close")
        )

        # ---------- Items ----------
        if items:
            self.set_items(items)

        # ---------- 选中 key 同步到 input ----------
        if self._selected_key is not None:
            it = self._listbox.item_by_key(self._selected_key)
            if it is not None:
                if not self._input_value:
                    self._input_value = it.title()
                    self._programmatic_text = True
                    self._input.set_text(self._input_value)
                    self._programmatic_text = False
                self._listbox.set_selected_keys({self._selected_key})

        # ---------- 事件 ----------
        self._input.text_changed.connect(self._on_input_changed)
        self._input.line_edit.installEventFilter(self)
        # focus 监听（菜单 trigger = focus）
        self._input.line_edit.installEventFilter(
            self
        )  # 同一 filter 既处理键盘又处理焦点

        # ---------- disabled keys ----------
        # 走统一入口:同时考虑用户传入的 disabled_keys + readonly 状态(readonly
        # 时整表 disabled,对齐 HeroUI 语义"列表照常打开但任何条目都选不了")。
        self._apply_disabled_state()

        # ---------- 主题注册 ----------
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

        # ---------- 初始 clear 按钮显隐 ----------
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
        # Input / Listbox / Popover / ScrollShadow 都是 theme="auto" 自己监听
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
        self._popover.set_theme(theme) if hasattr(self._popover, "set_theme") else None
        self._scroll.set_theme(theme) if hasattr(self._scroll, "set_theme") else None
        self._refresh_end_icons()

    # ============================================================
    # Items 装配
    # ============================================================
    def set_items(self, items: Iterable[Union[dict, tuple, ListboxItem]]):
        """重置 items 列表。

        item 可以是:
          - ``dict`` 形如 ``{"key":..., "label":..., "description":...,
                              "start_content":..., "end_content":...,
                              "shortcut":..., "is_disabled":...}``
          - ``(key, label)`` 二元 tuple
          - 现成的 :class:`ListboxItem` 实例
        """
        self._listbox.clear()
        self._items_data.clear()

        for raw in items:
            it = self._make_item(raw)
            self._items_data.append({"key": it.key(), "label": it.title()})
            self._listbox.add_item(it)
        # 同步 disabled / selected
        self._apply_disabled_state()
        if self._selected_key is not None:
            self._listbox.set_selected_keys({self._selected_key})
        self._apply_filter()

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
        # fallback: 把 str 当 label = key
        return ListboxItem(str(raw), key=str(raw))

    def items(self) -> list[ListboxItem]:
        return self._listbox.items()

    def item_by_key(self, key: str) -> Optional[ListboxItem]:
        return self._listbox.item_by_key(key)

    # ============================================================
    # 公共 getter / setter
    # ============================================================
    def selected_key(self) -> Optional[str]:
        return self._selected_key

    def set_selected_key(self, key: Optional[str]):
        if key == self._selected_key:
            return
        self._selected_key = key
        if key is None:
            self._listbox.set_selected_keys(set())
        else:
            self._listbox.set_selected_keys({key})
            it = self._listbox.item_by_key(key)
            if it is not None:
                self._programmatic_text = True
                self._input.set_text(it.title())
                self._input_value = it.title()
                self._programmatic_text = False
        self._refresh_clear_visibility()
        self.selection_changed.emit(key)

    def input_value(self) -> str:
        return self._input_value

    def set_input_value(self, text: str):
        text = text or ""
        if text == self._input_value:
            return
        self._input_value = text
        self._programmatic_text = True
        self._input.set_text(text)
        self._programmatic_text = False
        self._refresh_clear_visibility()
        self._apply_filter()
        self.input_changed.emit(text)

    def is_open(self) -> bool:
        return self._is_open

    def _popover_max_height(self) -> int:
        cfg_ac = AUTOCOMPLETE_SIZES.get(self._size, AUTOCOMPLETE_SIZES["md"])
        return int(cfg_ac["popover_max_height"])

    def _available_scroll_height_below(self) -> int:
        """计算从 input 下沿到屏幕底部最多还能放下多少 scroll 内容高度。"""
        screen = QApplication.primaryScreen()
        if screen is None:
            return self._popover_max_height()
        rect = screen.availableGeometry()
        pos = self._input.mapToGlobal(QPoint(0, 0))
        # Popover bottom-start 公式：y = input_bottom - top_margin + gap；
        # popover bottom = input_bottom + gap + scroll_height + bottom_margin。
        # 因此 scroll_height 不能超过 screen_bottom - input_bottom - gap - bottom_margin。
        gap = 6
        _, _, _, bottom_margin = self._popover._frame_margins()
        return int(rect.bottom() - (pos.y() + self._input.height()) - gap - bottom_margin)

    def _visible_listbox_content_height(self) -> int:
        """计算 Listbox 当前可见内容高度。

        不能直接用 Listbox.sizeHint()：QScrollArea 包裹后它常返回约 100px；
        也不能直接用 _list.sizeHint()：过滤时 hidden item 可能仍影响 hint。
        这里按当前未 hidden 的 item/section 手动累加，保证下拉高度受内容和
        popover_max_height 双重约束。
        """
        try:
            cfg_outer = self._listbox._outer.contentsMargins()
            gap = self._listbox._list_v.spacing()
            visible_widgets = [
                self._listbox._list_v.itemAt(i).widget()
                for i in range(self._listbox._list_v.count())
            ]
            visible_widgets = [
                w for w in visible_widgets
                if w is not None and not w.isHidden()
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
        """刷新下拉高度。

        上一个版本的核心语义是：``popover_max_height`` 是真正的滚动视口上限，
        列表超过这个高度就被限制在这个盒子里滚动，而不是让内容自然撑开。
        现在 token 翻倍后也保持这个语义：内容超过旧上限（即新上限的一半）时，
        直接使用新上限；只有很短的列表才按内容自然收缩。
        """
        token_max = self._popover_max_height()
        max_h = token_max
        if prefer_below:
            max_h = min(max_h, self._available_scroll_height_below())
        max_h = min(token_max, max(80, int(max_h)))

        content_h = max(1, self._visible_listbox_content_height())
        # 旧版上限正好是新版 token 的一半：sm 220 / md 260 / lg 300。
        # 超过旧上限的列表视为"需要滚动的长列表"，高度固定到新版上限，
        # 不再跟 item 数量上下漂移成 468/496 这种内容撑开高度。
        old_cap = max(80, token_max // 2)
        if content_h > old_cap:
            target = max_h
        else:
            target = min(content_h, max_h)
            target = max(80, int(target))

        self._scroll.setMinimumHeight(target)
        self._scroll.setMaximumHeight(max_h)
        self._scroll.updateGeometry()

    def open(self, trigger: str = "manual"):
        if self._is_disabled or self._is_open:
            return
        self._pending_trigger = trigger
        # 让 popover 宽度 = input 实际渲染宽度(对齐 HeroUI:下拉与输入框等宽)。
        # 构造期只能拿到 sizeHint(),但 input 常被父布局拉宽 → sizeHint < 实际宽度;
        # 必须在 open 时用 .width() 拿当前几何,再下发给 scroll 内层 + popover 自身。
        w = max(self._input.width(), self._input.sizeHint().width())
        self._scroll.setMinimumWidth(w)
        self._scroll.setMaximumWidth(w)
        self._refresh_popover_height(prefer_below=True)
        self._popover.open(near=self._input)

    def close(self):
        if not self._is_open:
            return
        self._popover.close()

    def toggle(self, trigger: str = "manual"):
        if self._is_open:
            self.close()
        else:
            self.open(trigger)

    # ============================================================
    # 透传 setter (Input)
    # ============================================================
    def set_label(self, label: str):
        self._input.set_label(label)

    def set_placeholder(self, placeholder: str):
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
        # 默认 listbox_color 跟随 color
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

    def set_radius(self, radius: Optional[str]):
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
        self._input.set_is_readonly(v)
        # readonly 改变时刷新列表 disabled 状态:对齐 HeroUI 语义,
        # readonly=True 时整表禁选(列表仍可打开浏览,但任意条目不可选)。
        self._apply_disabled_state()

    def set_is_clearable(self, v: bool):
        self._is_clearable = bool(v)
        self._refresh_clear_visibility()

    def set_allows_custom_value(self, v: bool):
        self._allows_custom_value = bool(v)

    def set_default_filter(self, fn: Optional[Callable[[str, str], bool]]):
        self._filter = fn or _default_contains_filter
        self._apply_filter()

    def set_disabled_keys(self, keys: Iterable[str]):
        self._disabled_keys = set(keys)
        self._apply_disabled_state()

    def _apply_disabled_state(self) -> None:
        """统一计算并下发 listbox 的 disabled keys。

        规则（对齐 HeroUI v2 Autocomplete.isReadOnly 语义）:
            - readonly=False: 直接用用户传入的 self._disabled_keys
            - readonly=True : 把当前所有 item 的 key 都加进 disabled —— 列表仍可
              打开浏览,但任何条目都点不动。这正好是 HeroUI 文档说的:
              "如果你把 isReadOnly 属性传递给自动补全，列表框会打开显示所有
              可用选项,但用户无法选择任何列出的选项"

        每次调用都全量计算下发,避免增量同步出错。所有触发点(构造、items 变更、
        set_disabled_keys、set_is_readonly)都走这一个入口。
        """
        if self._input._is_readonly:
            all_keys = {it.key() for it in self._listbox.items()}
            effective = self._disabled_keys | all_keys
        else:
            effective = set(self._disabled_keys)
        self._listbox.set_disabled_keys(effective)

    def set_empty_content(self, text: Optional[str]):
        self._empty_content = text
        self._listbox.set_empty_content(text)

    def set_disable_selector_icon_rotation(self, v: bool):
        self._disable_selector_icon_rotation = bool(v)
        if v:
            self._end.selector_btn.set_angle(0, animated=False)
        else:
            target = 180.0 if self._is_open else 0.0
            self._end.selector_btn.set_angle(target, animated=False)

    # ============================================================
    # Filter
    # ============================================================
    def _apply_filter(self):
        """根据 _input_value 把不匹配的 listbox item hide。"""
        query = self._input_value or ""
        for it in self._listbox.items():
            # 不过滤 disabled 项的可见性（disabled 仍占位，符合 HeroUI 行为）
            match = self._filter(it.title(), query)
            it.setVisible(match)
        # popover 内 listbox 的 empty 状态：用 not isHidden() 计数（isVisible 在 popover
        # 未 show 时不可靠）
        visible_count = sum(1 for it in self._listbox.items() if not it.isHidden())
        self._listbox._empty_widget.setVisible(visible_count == 0)
        self._listbox.updateGeometry()
        self._refresh_popover_height(prefer_below=self._is_open)

# ============================================================
# Aliases — 对齐 HeroUI 文档的 `<AutocompleteItem>` / `<AutocompleteSection>`
# 这两个类的所有 props 直接继承自 ListboxItem / ListboxSection
# （HeroUI 文档原话："Inherits all props from ListboxItem/Section"）。
# ============================================================
AutocompleteItem = ListboxItem
AutocompleteSection = ListboxSection
