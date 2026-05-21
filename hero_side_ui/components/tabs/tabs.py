"""HeroSideUI Tabs Component — 标签页容器。

子组件：
    - ``_CursorWidget`` → ``_cursor.py`` （选中态滑动光标）
    - ``TabItem``       → ``item.py``    （单个标签）
    - ``_TabList``      → ``_tab_list.py``（标签容器）
"""

from PySide6.QtWidgets import QBoxLayout

from PySide6.QtCore import QTimer
from typing import List

from typing import Callable, Optional, Union

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...animation import stop_tween, tween_geometry, tween_value
from ...core import ThemeProvider
from ...themes import HEROUI_COLORS, RADIUS, TABS_SIZES
from ...utils import load_svg_icon

from ._constants import (
    VALID_COLORS,
    VALID_PLACEMENTS,
    VALID_RADIUS,
    VALID_SIZES,
    VALID_THEMES,
    VALID_VARIANTS,
)
from ._cursor import _CursorWidget
from ._helpers import _resolve_radius_px
from ._tab_list import _TabList
from .item import TabItem

# ============================================================
# Tabs: 主组件
# ============================================================


class Tabs(QWidget):
    """HeroUI Tabs 组件 —— 完整复刻。

    选中变更信号: selection_changed(int index, str key)
    """

    CURSOR_ANIM_DURATION = 250

    selection_changed = Signal(int, str)

    def __init__(
        self,
        items: Optional[List[Union[str, tuple, dict]]] = None,
        *,
        variant: str = "solid",
        color: str = "default",
        size: str = "md",
        radius: Optional[str] = None,
        placement: str = "top",
        theme: str = "auto",
        full_width: bool = False,
        is_disabled: bool = False,
        disable_animation: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # 校验
        if variant not in VALID_VARIANTS:
            raise ValueError(f"variant must be one of {VALID_VARIANTS}")
        if color not in VALID_COLORS:
            raise ValueError(f"color must be one of {VALID_COLORS}")
        if size not in VALID_SIZES:
            raise ValueError(f"size must be one of {VALID_SIZES}")
        if placement not in VALID_PLACEMENTS:
            raise ValueError(f"placement must be one of {VALID_PLACEMENTS}")
        if theme not in ("auto", *VALID_THEMES):
            raise ValueError(f"theme must be one of ('auto', {VALID_THEMES})")

        self._variant = variant
        self._color = color
        self._size = size
        # underlined 强制 rounded-none（compoundSlots）
        if variant == "underlined":
            self._radius = "none"
        else:
            self._radius = radius if radius is not None else "md"
        self._placement = placement
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._full_width = bool(full_width)
        self._is_disabled = bool(is_disabled)
        self._disable_animation = bool(disable_animation)

        self._tabs: List[TabItem] = []
        self._panels: List[QWidget] = []
        self._current_index = -1
        self._cursor_initialized = False

        # ----- 构建 UI -----
        # 外层 wrapper (用 QBoxLayout, 方向由 placement 决定)
        self._wrapper_layout = QBoxLayout(QBoxLayout.TopToBottom, self)
        self._wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self._wrapper_layout.setSpacing(0)

        # tabList
        self._list = _TabList(self)
        self._list_layout = QHBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(TABS_SIZES[size]["list_gap"])

        # cursor 在 list 上层，但是 z 序在所有 tab 之下
        self._cursor = _CursorWidget(self._list)
        self._cursor.lower()

        # ButtonGroup 处理互斥
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self._on_id_clicked)

        # panels
        self._stack = QStackedWidget(self)

        # 装配
        self._wrapper_layout.addWidget(self._list)
        self._wrapper_layout.addWidget(self._stack)

        # 应用 placement
        self._apply_placement()
        self._apply_styles()
        self._apply_disabled_state()

        # 添加初始 items
        if items:
            for it in items:
                if isinstance(it, str):
                    self.add_tab(it)
                elif isinstance(it, tuple):
                    # (title, content) 或 (title, content, key)
                    if len(it) == 2:
                        self.add_tab(it[0], it[1])
                    elif len(it) == 3:
                        self.add_tab(it[0], it[1], key=it[2])
                elif isinstance(it, dict):
                    self.add_tab(
                        it.get("title", ""),
                        it.get("content"),
                        key=it.get("key"),
                        disabled=it.get("disabled", False),
                        start_icon=it.get("start_icon"),
                        end_icon=it.get("end_icon"),
                        custom=it.get("custom"),
                    )

        # 自动选中第一个可用 tab
        QTimer.singleShot(0, self._auto_select_first)

        # auto 模式：注册到 ThemeProvider
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # Public API
    # ============================================================

    def add_tab(
        self,
        title: str = "",
        content: Optional[QWidget] = None,
        *,
        key: Optional[str] = None,
        disabled: bool = False,
        start_icon=None,
        end_icon=None,
        custom: Optional[QWidget] = None,
    ) -> TabItem:
        """添加一个 tab。

        三档插槽：
          1. 纯文本: ``add_tab("Photos")``
          2. icon + 文本: ``add_tab("Photos", start_icon="heroicons--photo-solid")``
          3. 完全自定义 tab 标签: ``add_tab(custom=my_widget)``（``title`` 仅作 key fallback）

        ``content`` 始终是 panel 内容（任意 QWidget），独立于 tab 标签外观。
        """
        tab = TabItem(
            title,
            key=key,
            start_icon=start_icon,
            end_icon=end_icon,
            custom=custom,
            parent=self._list,
        )
        if disabled:
            tab.set_disabled(True)
        # 加入 group + layout
        idx = len(self._tabs)
        self._group.addButton(tab, idx)
        self._list_layout.addWidget(tab)
        self._tabs.append(tab)

        # 内容面板：用户没传则给一个空 QWidget
        panel = content if content is not None else QWidget()
        self._panels.append(panel)
        self._stack.addWidget(panel)

        tab.apply_style(
            variant=self._variant,
            color=self._color,
            size=self._size,
            theme=self._theme,
            disable_animation=self._disable_animation,
            full_width=self._full_width,
        )
        return tab

    def remove_tab(self, index: int):
        if not 0 <= index < len(self._tabs):
            return
        tab = self._tabs.pop(index)
        panel = self._panels.pop(index)
        self._group.removeButton(tab)
        self._list_layout.removeWidget(tab)
        tab.setParent(None)
        tab.deleteLater()
        self._stack.removeWidget(panel)
        # 重新映射 button id
        for i, t in enumerate(self._tabs):
            self._group.setId(t, i)
        if self._current_index >= len(self._tabs):
            self._current_index = len(self._tabs) - 1
        if self._current_index >= 0:
            self.set_selected(self._current_index, animate=False)

    def clear(self):
        while self._tabs:
            self.remove_tab(0)
        self._current_index = -1

    def count(self) -> int:
        return len(self._tabs)

    def tab_at(self, index: int) -> Optional[TabItem]:
        if 0 <= index < len(self._tabs):
            return self._tabs[index]
        return None

    def panel_at(self, index: int) -> Optional[QWidget]:
        if 0 <= index < len(self._panels):
            return self._panels[index]
        return None

    def current_index(self) -> int:
        return self._current_index

    def current_key(self) -> Optional[str]:
        if 0 <= self._current_index < len(self._tabs):
            return self._tabs[self._current_index].key()
        return None

    def set_selected(self, index_or_key: Union[int, str], *, animate: bool = True):
        """切换到指定 tab。"""
        if isinstance(index_or_key, str):
            index = next(
                (i for i, t in enumerate(self._tabs) if t.key() == index_or_key), -1
            )
        else:
            index = int(index_or_key)
        if not 0 <= index < len(self._tabs):
            return
        target = self._tabs[index]
        if target.is_disabled():
            return
        prev = self._current_index
        self._current_index = index

        do_animate = animate and not self._disable_animation

        # 更新所有 tab 的选中态。两种路径：
        # - 带动画：用 setChecked，QButtonGroup 排他自动反选其他 tab，toggled 信号驱动文字色动画
        # - 不带动画：用 set_checked_silent，block toggled 信号 + 直接刷颜色，避免开屏闪
        if do_animate:
            for i, t in enumerate(self._tabs):
                checked = i == index
                if t.isChecked() != checked:
                    t.setChecked(checked)
        else:
            for i, t in enumerate(self._tabs):
                checked = i == index
                if t.isChecked() != checked:
                    t.set_checked_silent(checked)

        self._stack.setCurrentIndex(index)
        # 移动 cursor
        self._move_cursor_to(index, animate=animate and self._cursor_initialized)
        if not self._cursor_initialized:
            self._cursor_initialized = True
        if prev != index:
            self.selection_changed.emit(index, target.key())

    # -------- 动态 setter --------

    # -------- 动态 setter --------

    def _validate(self, name: str, value: str, valid):
        if value not in valid:
            raise ValueError(f"{name} must be one of {tuple(valid)}")

    def _reposition_cursor_async(self):
        QTimer.singleShot(
            0, lambda: self._move_cursor_to(self._current_index, animate=False)
        )

    def set_variant(self, variant: str):
        self._validate("variant", variant, VALID_VARIANTS)
        self._variant = variant
        if variant == "underlined":
            self._radius = "none"
        self._apply_styles()
        self._move_cursor_to(self._current_index, animate=False)

    def set_color(self, color: str):
        self._validate("color", color, VALID_COLORS)
        self._color = color
        self._apply_styles()

    def set_size(self, size: str):
        self._validate("size", size, VALID_SIZES)
        self._size = size
        self._list_layout.setSpacing(TABS_SIZES[size]["list_gap"])
        self._apply_styles()
        self._reposition_cursor_async()

    def set_radius(self, radius: str):
        self._validate("radius", radius, VALID_RADIUS)
        if self._variant == "underlined":
            radius = "none"
        self._radius = radius
        self._apply_styles()
        self._reposition_cursor_async()

    def set_placement(self, placement: str):
        self._validate("placement", placement, VALID_PLACEMENTS)
        self._placement = placement
        self._apply_placement()
        self._apply_styles()
        self._reposition_cursor_async()

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            self._validate("theme", theme, VALID_THEMES)
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用"""
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    def set_full_width(self, full: bool):
        self._full_width = bool(full)
        self._apply_styles()

    def set_disabled(self, disabled: bool):
        self._is_disabled = bool(disabled)
        self._apply_disabled_state()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = bool(disable)
        for t in self._tabs:
            t._disable_animation = self._disable_animation

    def _apply_placement(self):
        """根据 placement 重新组合 wrapper layout 方向。"""
        # tabList 内部方向
        # top/bottom -> 水平 list；start/end -> 垂直 list
        self._list_layout.setDirection(
            QBoxLayout.LeftToRight
            if self._placement in ("top", "bottom")
            else QBoxLayout.TopToBottom
        )
        # wrapper 方向：top -> TopToBottom; bottom -> BottomToTop
        # start -> LeftToRight; end -> RightToLeft
        mapping = {
            "top": QBoxLayout.TopToBottom,
            "bottom": QBoxLayout.BottomToTop,
            "start": QBoxLayout.LeftToRight,
            "end": QBoxLayout.RightToLeft,
        }
        self._wrapper_layout.setDirection(mapping[self._placement])

        # cursor 重新刷
        self._cursor.configure(placement=self._placement)

    def _apply_styles(self):
        """根据当前所有属性应用样式。"""
        cfg = TABS_SIZES[self._size]

        # 估算 tabList 高度，用于 full radius
        if self._placement in ("top", "bottom"):
            est_h = cfg["tab_height"] + 2 * cfg["list_padding"]
        else:
            est_h = cfg["tab_height"]

        list_radius_px, tab_radius_px = _resolve_radius_px(
            self._radius, self._size, est_h
        )
        # underlined 强制无圆角（compoundSlots）
        if self._variant == "underlined":
            list_radius_px = 0
            tab_radius_px = 0

        # 配置 list
        border_w = cfg["border_width"] if self._variant == "bordered" else 0
        self._list.configure(
            variant=self._variant,
            theme=self._theme,
            radius_px=list_radius_px,
            border_width=border_w,
        )
        list_pad = cfg["list_padding"]
        # underlined / light / bordered 不需要 padding（保持紧凑）
        # solid 才需要内 padding 露出底色
        if self._variant in ("solid",):
            self._list_layout.setContentsMargins(list_pad, list_pad, list_pad, list_pad)
        elif self._variant == "bordered":
            self._list_layout.setContentsMargins(list_pad, list_pad, list_pad, list_pad)
        else:
            self._list_layout.setContentsMargins(0, 0, 0, 0)

        # 配置 cursor
        self._cursor.configure(
            variant=self._variant,
            color=self._color,
            theme=self._theme,
            radius_px=tab_radius_px,
            placement=self._placement,
            underline_h=cfg["underline_h"],
            underline_ratio=cfg["underline_ratio"],
        )

        # 应用到每个 tab
        for t in self._tabs:
            t.apply_style(
                variant=self._variant,
                color=self._color,
                size=self._size,
                theme=self._theme,
                disable_animation=self._disable_animation,
                full_width=self._full_width,
            )

        # full_width
        if self._full_width:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            if self._placement in ("top", "bottom"):
                self._list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            else:
                self._list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self._list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # panel padding
        if self._placement in ("start", "end"):
            self._stack.setContentsMargins(
                cfg["panel_padding_h_side"],
                cfg["panel_padding_v_side"],
                cfg["panel_padding_h_side"],
                cfg["panel_padding_v_side"],
            )
        else:
            self._stack.setContentsMargins(
                cfg["panel_padding_h"],
                cfg["panel_padding_v"],
                cfg["panel_padding_h"],
                cfg["panel_padding_v"],
            )

        # underlined 时 list_layout spacing 略增
        self._list_layout.setSpacing(cfg["list_gap"])

        self._list.update()

    def _apply_disabled_state(self):
        """tabList 整体禁用 -> 50% 透明 + 屏蔽点击。"""
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        if self._is_disabled:
            eff = QGraphicsOpacityEffect(self._list)
            eff.setOpacity(0.5)
            self._list.setGraphicsEffect(eff)
            self._list.setEnabled(False)
        else:
            self._list.setGraphicsEffect(None)
            self._list.setEnabled(True)

    def _on_id_clicked(self, idx: int):
        if not 0 <= idx < len(self._tabs):
            return
        if self._tabs[idx].is_disabled():
            return
        if idx == self._current_index:
            return
        self.set_selected(idx)

    def _auto_select_first(self):
        if self._current_index == -1 and self._tabs:
            for i, t in enumerate(self._tabs):
                if not t.is_disabled():
                    self.set_selected(i, animate=False)
                    break

    def _move_cursor_to(self, index: int, *, animate: bool):
        if not 0 <= index < len(self._tabs):
            self._cursor.hide()
            return
        target_geom = QRect(self._tabs[index].geometry())

        # 首次 / disable_animation / cursor 还没显示过 —— 直接到位
        if not animate or self._disable_animation or not self._cursor.isVisible():
            stop_tween(self._cursor, "_cursor_anim_runner")
            self._cursor.setGeometry(target_geom)
            self._cursor.show()
            self._cursor.lower()
            return

        tween_geometry(
            self._cursor,
            "_cursor_anim_runner",
            target_geom,
            duration=self.CURSOR_ANIM_DURATION,
        )
        self._cursor.lower()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        # 让 cursor 紧跟当前 tab 的几何
        self._reposition_cursor_async()

    def showEvent(self, ev):
        super().showEvent(ev)
        self._reposition_cursor_async()


__all__ = ["Tabs", "TabItem"]
