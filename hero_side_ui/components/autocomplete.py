"""
HeroSideUI Autocomplete Component
基于 HeroUI v2 设计风格

样式来源:
    https://github.com/heroui-inc/heroui/tree/main/packages/components/autocomplete
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/autocomplete.ts

架构 (完全组合，零修改既有组件):

    Autocomplete (QWidget 容器)
        └── Input                                  (复用，所有 Input props 透传)
              └── end_content = _EndContentWidget  (注入复合右侧内容)
                    ├── _ClearButton               (data-visible 等价: input 有值 或 有选中)
                    └── _SelectorButton            (chevron-down，点击 toggle popover)
        └── Popover                                (manual 触发，绑定 input)
              └── ScrollShadow                     (滚动渐变阴影)
                    └── Listbox                    (selection_mode="single")
                          └── ListboxItem ×N       (按 contains filter 决定 setVisible)

数据流（对齐 use-autocomplete）:

    _input_value      当前输入框文本
    _selected_key     当前选中 key (None 表示无)
    _is_open          popover 显隐

    用户输入       → filter items → 不匹配的 setVisible(False) → popover 自动打开
    点击 Listbox 项 → input.text = item.label / _selected_key = item.key / popover 关闭
    点击 selector   → toggle popover
    点击 clear      → input.text = "" / _selected_key = None / popover 打开 / 焦点回 input
    input focus    → 若 menu_trigger="focus" 打开 popover
    Esc            → 关闭 popover
    Enter          → 选中当前 listbox 焦点项；popover 关闭时不动
    ↑↓             → 焦点在 listbox 中可见 item 之间移动；popover 关闭时打开

过滤（对齐 useFilter.contains, sensitivity:base）:
    default_filter(item_label: str, query: str) -> bool
        默认: query.lower() in item_label.lower() (空 query 全显示)
    用户可传 default_filter 覆盖

allows_custom_value (对齐源码):
    False (默认)：blur 时若 input.text 不匹配任何 item.label，
                  回退到 _selected_key 对应 label（或清空）
    True       ：保留用户输入

主题 (theme="auto" 默认):
    注册到 ThemeProvider；切换时把 theme 转发给 Input / Listbox / Popover
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
    QGraphicsRotation,
    QApplication,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QEvent,
    QObject,
    QSize,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QPalette,
    QFont,
    QIcon,
    QPixmap,
    QPainter,
    QTransform,
)
from typing import Callable, Iterable, List, Optional, Union

from ..themes import (
    HEROUI_COLORS,
    RADIUS,
    FONT_FAMILY,
    AUTOCOMPLETE_SIZES,
    INPUT_SIZES,
)
from ..utils import load_svg_icon
from ..animation import tween_value, stop_tween
from ..core import ThemeProvider

from .input import Input
from .listbox import Listbox, ListboxItem, ListboxSection
from .popover import Popover, PopoverContent
from .scroll_shadow import ScrollShadow
from .button import Button


# ============================================================
# 默认过滤器: contains, case-insensitive
# ============================================================
def _default_contains_filter(item_label: str, query: str) -> bool:
    if not query:
        return True
    return query.lower() in item_label.lower()


# ============================================================
# Selector 按钮：能 tween 旋转
# ============================================================
class _SelectorButton(QPushButton):
    """selectorButton：底层 svg 图标 + 通过 QTransform 旋转动画。

    由于 QIcon 已经 rasterize，QSS `transform: rotate()` 在 PySide 无效；
    我们自己 paint 时把 pixmap 用 QTransform 旋转 ``self._angle`` 角度。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFlat(True)
        self.setStyleSheet("border: 0; background: transparent; padding: 0;")
        self._pixmap: Optional[QPixmap] = None
        self._angle: float = 0.0  # 0=指向下；180=指向上
        self._angle_anim_runner = None  # tween runner

    def set_pixmap(self, pix: QPixmap):
        self._pixmap = pix
        self.update()

    def angle(self) -> float:
        return self._angle

    def set_angle(self, deg: float, *, animated: bool, duration: int = 150):
        if animated and self._angle != deg:
            tween_value(
                self,
                "_angle_anim_runner",
                float(self._angle),
                float(deg),
                self._on_angle_step,
                duration=duration,
            )
        else:
            self._angle = deg
            self.update()

    def _on_angle_step(self, v):
        self._angle = float(v)
        self.update()

    def paintEvent(self, e):
        if self._pixmap is None or self._pixmap.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.Antialiasing, True)
        # 在 button 中心绘制旋转后的 pixmap
        cx = self.width() / 2
        cy = self.height() / 2
        p.translate(cx, cy)
        p.rotate(self._angle)
        w = self._pixmap.width()
        h = self._pixmap.height()
        # 高 DPI 时 pixmap 实际像素是 deviceWidth/PixelRatio
        dpr = self._pixmap.devicePixelRatio() or 1.0
        dw = w / dpr
        dh = h / dpr
        p.drawPixmap(int(-dw / 2), int(-dh / 2), self._pixmap)
        p.end()


# ============================================================
# Clear 按钮：data-visible 行为
# ============================================================
# 历史:这里曾经有 _ClearButton 手写 QPushButton —— 因为 16/14 px 的 x-mark icon
# 在 Fusion QPushButton 默认 setIcon 路径下会被裁掉左侧。
# 后来用户做了 16-design 的 heroicons--x-mark-16-solid(viewBox 16,path 在 4-12
# 范围内,有充足 padding),配合 HeroSideUI 自己的 Button 组件就完全够用了 ——
# 直接在 _EndContentWidget 里实例化 Button 即可,不需要再有 _ClearButton 类。
# Button 的 icon 着色、hover bg、ripple 都是组件内置能力(铁律 3「高层意图 API」)。


# ============================================================
# endContentWrapper: [clear] + [selector]，对齐 HeroUI endContentWrapper slot
# ============================================================
class _EndContentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._h = QHBoxLayout(self)
        # 左边 margin 8px:让 clear 按钮与 input 文本之间有清晰间距,不"贴脸"
        # (用户反馈:之前 clear 看起来像被裁进文本区,实际是缺左 margin)。
        # 右 0、上下 0:popover 触发钮与 input 右内边对齐。
        self._h.setContentsMargins(8, 0, 0, 0)
        # clear 与 selector 之间 4px:两个按钮视觉上独立,而不是粘在一起。
        self._h.setSpacing(4)
        self._h.setAlignment(Qt.AlignVCenter)

        # clear 按钮:用 HeroSideUI 自己的 Button 组件(铁律 3「高层意图 API」)。
        # variant=light(无底,hover 才出淡灰) + radius=full(圆形点击区) +
        # icon_only + size=sm。icon 颜色 / hover bg / ripple 全部 Button 内部
        # 自管理 —— autocomplete 不需要手算 icon_color。
        # setFixedSize 在外部 _refresh_end_btn_sizes 中强制覆盖 Button 自己
        # icon_only 时算的 fixed size,让按钮严丝合缝嵌进 input row 高度。
        self.clear_btn = Button(
            variant="light",
            color="default",
            size="sm",
            radius="full",
            icon_only=True,
        )
        self.clear_btn.setFocusPolicy(Qt.NoFocus)
        self.clear_btn.hide()
        self._h.addWidget(self.clear_btn, 0, Qt.AlignVCenter)

        self.selector_btn = _SelectorButton(self)
        self._h.addWidget(self.selector_btn, 0, Qt.AlignVCenter)


# ============================================================
# Autocomplete
# ============================================================
class Autocomplete(QWidget):
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
        # 高度上限：popover_max_height
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
        cfg_ac = AUTOCOMPLETE_SIZES.get(size, AUTOCOMPLETE_SIZES["md"])
        self._scroll.setMaximumHeight(cfg_ac["popover_max_height"])
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
    # 内部：图标/尺寸刷新
    # ============================================================
    def _refresh_end_btn_sizes(self):
        cfg = AUTOCOMPLETE_SIZES.get(self._size, AUTOCOMPLETE_SIZES["md"])
        size = cfg["end_btn_size"]
        # clear_btn 是 Button 组件:用 set_icon_only_side(持久化 override),
        # 不能直接 setFixedSize —— Button._apply_styles 在主题切换时会被 ThemeProvider
        # 触发,把 setFixedSize 重新设回 BUTTON_SIZES 算的 30/... px。
        self._end.clear_btn.set_icon_only_side(size)
        self._end.selector_btn.setFixedSize(size, size)
        self._end._h.setSpacing(cfg["end_gap"])

    def _refresh_end_icons(self):
        cfg = AUTOCOMPLETE_SIZES.get(self._size, AUTOCOMPLETE_SIZES["md"])

        # Clear 按钮:用 Button 组件的高层 API —— 只传 icon name + size,
        # 颜色完全交给 Button 内部(light variant + default color 会渲染成柔和灰,
        # hover 时也会自动出 light hover bg)。铁律 3「高层意图 API」落地。
        self._end.clear_btn.set_icon(self._clear_icon)
        self._end.clear_btn.set_icon_size(cfg["clear_icon_size"])

        # Selector chevron 颜色策略(对齐用户要求点 4):
        # - color == "default" → 用 default-500(灰)
        # - color != "default" → 用对应 palette 的 500 色,与组件主色呼应
        if self._color != "default":
            sel_color = QColor(HEROUI_COLORS[self._color][500])
        else:
            sel_color = QColor(HEROUI_COLORS["default"][500])

        sel_pix = load_svg_icon(
            self._selector_icon,
            size=cfg["selector_icon_size"],
            color=sel_color,
            stroke_width=2.5,
        )
        self._end.selector_btn.set_pixmap(sel_pix)

    def _refresh_clear_visibility(self):
        has_value = bool(self._input_value) or self._selected_key is not None
        # 显示规则(对齐 HeroUI):
        #   1. is_clearable 开
        #   2. 有值
        #   3. 非 disabled / 非 readonly
        #   4. 容器被 hover **或** 当前已聚焦(focus 时也保留 clear,方便键盘流操作)
        # focus 时保留:用户可能用 Tab 切到这个 input,没移鼠标,不该突然失去 clear
        is_focused = self._input.line_edit.hasFocus() or self._is_open
        show = (
            self._is_clearable
            and has_value
            and not self._is_disabled
            and not self._input._is_readonly
            and (self._is_hovered or is_focused)
        )
        self._end.clear_btn.setVisible(show)

    # ============================================================
    # Hover 跟踪 —— 决定 clear 按钮显隐
    # ============================================================
    def enterEvent(self, event):
        self._is_hovered = True
        self._refresh_clear_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._refresh_clear_visibility()
        super().leaveEvent(event)

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

    # ============================================================
    # 事件
    # ============================================================
    def _on_input_changed(self, text: str):
        if self._programmatic_text:
            self._input_value = text
            return
        self._input_value = text
        # 用户键入 → 清除 selected_key（HeroUI 行为）
        if self._selected_key is not None:
            # 判断：如果新 text 还是当前 selected 的 label 不变（textChanged 重复触发），
            # 不要把 selected 清掉
            it = self._listbox.item_by_key(self._selected_key)
            if it is None or it.title() != text:
                self._selected_key = None
                self._listbox.set_selected_keys(set())
                self.selection_changed.emit(None)
        self._apply_filter()
        self._refresh_clear_visibility()
        # 打开 popover（typing trigger）
        if not self._is_open and self._menu_trigger != "manual":
            self.open(trigger="input")
        self.input_changed.emit(text)

    def _on_listbox_action(self, key: str):
        """用户在 listbox 点击某项。"""
        it = self._listbox.item_by_key(key)
        if it is None:
            return
        new_text = it.title()
        # 选中 key
        self._selected_key = key
        self._listbox.set_selected_keys({key})
        # 同步 input.text
        if new_text != self._input_value:
            self._programmatic_text = True
            self._input.set_text(new_text)
            self._input_value = new_text
            self._programmatic_text = False
            self.input_changed.emit(new_text)
        self._refresh_clear_visibility()
        self.selection_changed.emit(key)
        # 守卫位 _just_committed：让 Qt 在 popover 关闭时自动还焦点给 line_edit
        # 触发的 FocusIn 不会自动重开 popover。
        #
        # 关键设计：守卫不是按时间窗解锁，而是"事件序列"解锁 —— 只拦截
        # 接下来 line_edit 收到的第一个 FocusIn（即 Qt 自动 restore focus 那一发），
        # 命中后立刻解锁。这样无论用户手速多快、popover fade-out 多久，
        # 都不会误拦合法的"再次点击重开"操作。
        # 兜底：FocusIn 没来时（极端情况），200ms 后强制解锁，避免守卫卡死。
        self._just_committed = True
        self.close()
        QTimer.singleShot(200, lambda: setattr(self, "_just_committed", False))

    def _on_clear_clicked(self):
        self._selected_key = None
        self._listbox.set_selected_keys(set())
        self._programmatic_text = True
        self._input.set_text("")
        self._programmatic_text = False
        self._input_value = ""
        self._apply_filter()
        self._refresh_clear_visibility()
        self.selection_changed.emit(None)
        self.input_changed.emit("")
        self.cleared.emit()
        # 打开 popover + 焦点回 input（对齐 HeroUI 行为）
        if not self._is_open:
            self.open(trigger="clear")
        QTimer.singleShot(0, self._input.line_edit.setFocus)

    def _on_selector_clicked(self):
        if self._is_disabled:
            return
        self.toggle(trigger="manual")
        # 点击 selector 后焦点回 input
        QTimer.singleShot(0, self._input.line_edit.setFocus)

    def _on_popover_open_changed(self, is_open: bool, trigger: str):
        self._is_open = is_open
        # popover 打开/关闭都刷一次 clear:open 时即使无 hover 也保留(键盘流),
        # close 时若 hover 也没了就该收起。
        self._refresh_clear_visibility()
        # selector 图标旋转
        if not self._disable_selector_icon_rotation:
            cfg = AUTOCOMPLETE_SIZES.get(self._size, AUTOCOMPLETE_SIZES["md"])
            self._end.selector_btn.set_angle(
                180.0 if is_open else 0.0,
                animated=not self._disable_animation,
                duration=cfg["rotate_duration"],
            )
        # 打开时滚到选中项
        if is_open and self._selected_key is not None:
            # listbox 自己已经维护焦点；这里只确保选中项可见
            it = self._listbox.item_by_key(self._selected_key)
            if it is not None:
                (
                    self._scroll.ensureWidgetVisible(it)
                    if hasattr(self._scroll, "ensureWidgetVisible")
                    else None
                )
        # 关闭时处理 allows_custom_value
        if not is_open and not self._allows_custom_value:
            # 如果当前 input.text 不匹配任何 item.label，回退到 selected_key 的 label，
            # 没 selected_key 就清空
            current_text = self._input_value
            matched = False
            for it in self._listbox.items():
                if it.title() == current_text:
                    matched = True
                    break
            if not matched:
                if self._selected_key is not None:
                    it = self._listbox.item_by_key(self._selected_key)
                    if it is not None:
                        self._programmatic_text = True
                        self._input.set_text(it.title())
                        self._input_value = it.title()
                        self._programmatic_text = False
                        self.input_changed.emit(self._input_value)
                else:
                    if current_text:
                        self._programmatic_text = True
                        self._input.set_text("")
                        self._input_value = ""
                        self._programmatic_text = False
                        self.input_changed.emit("")
                self._apply_filter()
                self._refresh_clear_visibility()

        self.open_changed.emit(is_open, trigger)

    # ============================================================
    # 键盘 / 焦点 拦截
    # ============================================================
    def eventFilter(self, obj, event):
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
                if (
                    self._menu_trigger == "focus"
                    and not self._is_open
                    and not self._is_disabled
                ):
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
                        self._listbox._set_focus_index(
                            self._listbox.items().index(vis[0])
                        )
                    return True
                if key == Qt.Key_End and self._is_open:
                    vis = self._visible_items()
                    if vis:
                        self._listbox._set_focus_index(
                            self._listbox.items().index(vis[-1])
                        )
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
        # 用 not isHidden() 而非 isVisible() —— popover 关闭时 isVisible 会因祖先 hide
        # 返回 False，但 hide_state（即被 _apply_filter setVisible(False)）才是我们关心的
        return [
            it
            for it in self._listbox.items()
            if not it.isHidden() and not it.is_disabled()
        ]

    def _handle_arrow(self, down: bool):
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


__all__ = ["Autocomplete", "AutocompleteItem", "AutocompleteSection"]


# ============================================================
# Aliases — 对齐 HeroUI 文档的 `<AutocompleteItem>` / `<AutocompleteSection>`
# 这两个类的所有 props 直接继承自 ListboxItem / ListboxSection
# （HeroUI 文档原话："Inherits all props from ListboxItem/Section"）。
# ============================================================
AutocompleteItem = ListboxItem
AutocompleteSection = ListboxSection
