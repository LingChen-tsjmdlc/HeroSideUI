"""HeroSideUI Pagination 组件 — 复刻 HeroUI v2 Pagination。

子模块:
    - ``_PaginationItem`` (`./_item.py`): 单个按钮(页码/方向/省略号)
    - ``_CursorWidget``   (`./_cursor.py`): 滑动 + 弹簧光标
    - ``_DotsIcon``       (`./_ellipsis_icon.py`): hover 切换 ellipsis ↔ double-chevron
    - ``compute_pagination_range`` (`./_range.py`): 范围计算
    - ``_palette / _constants``: 颜色 / 枚举

公共信号: page_changed(int)
"""

from typing import Callable, List, Optional, Union

from PySide6.QtCore import QEasingCurve, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QSizePolicy,
    QWidget,
)

from ...animation import start_cursor_slide, stop_tween, tween_value
from ...core import ThemeProvider
from ...themes import PAGINATION_SIZES

from ._constants import (
    PaginationItemType,
    VALID_COLORS,
    VALID_RADII,
    VALID_SIZES,
    VALID_THEMES,
    VALID_VARIANTS,
)
from ._cursor import _CursorWidget
from ._item import _PaginationItem
from ._palette import resolve_radius_px
from ._range import compute_pagination_range


class Pagination(QWidget):
    """HeroUI v2 Pagination 复刻。

    构造参数对齐 HeroUI v2; 信号 ``page_changed(int)`` 等价 ``onChange``。
    """

    page_changed = Signal(int)

    # cursor 切换动画时长 (与 HeroUI CURSOR_TRANSITION_TIMEOUT=300ms 对齐)
    CURSOR_ANIM_DURATION = 300
    # cursor 首次淡入时长
    CURSOR_FADE_IN_MS = 200

    def __init__(
        self,
        total: int,
        *,
        initial_page: int = 1,
        page: Optional[int] = None,
        siblings: int = 1,
        boundaries: int = 1,
        dots_jump: int = 5,
        variant: str = "flat",
        color: str = "primary",
        size: str = "md",
        radius: str = "md",
        is_compact: bool = False,
        is_disabled: bool = False,
        show_controls: bool = False,
        loop: bool = False,
        disable_animation: bool = False,
        disable_cursor_animation: bool = False,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # ---- 校验 ----
        self._validate("variant", variant, VALID_VARIANTS)
        self._validate("color", color, VALID_COLORS)
        self._validate("size", size, VALID_SIZES)
        self._validate("radius", radius, VALID_RADII)
        if theme not in ("auto", *VALID_THEMES):
            raise ValueError(f"theme must be one of ('auto', {VALID_THEMES})")

        # ---- 状态 ----
        self._total = max(1, int(total))
        self._active_page = max(
            1, min(int(initial_page if page is None else page), self._total)
        )
        self._siblings = max(0, int(siblings))
        self._boundaries = max(0, int(boundaries))
        self._dots_jump = max(1, int(dots_jump))
        self._variant = variant
        self._color = color
        self._size = size
        self._radius = radius
        self._is_compact = bool(is_compact)
        self._is_disabled = bool(is_disabled)
        self._show_controls = bool(show_controls)
        self._loop = bool(loop)
        self._disable_animation = bool(disable_animation)
        self._disable_cursor_animation = (
            bool(disable_cursor_animation) or self._disable_animation
        )

        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        # 当前 range 和对应的 item widgets
        self._items: List[_PaginationItem] = []
        # active page 对应的 item (用于 cursor 跟踪)
        self._active_item: Optional[_PaginationItem] = None

        # cursor 动画状态
        self._cursor_x = 0.0
        self._cursor_anim_runner = None
        self._cursor_fade_runner = None
        self._cursor_first_show = True
        self._cursor_opacity_effect: Optional[QGraphicsOpacityEffect] = None
        # 待执行的 cursor 移动请求: True=带动画, False=静态, None=无
        self._cursor_pending_animate: Optional[bool] = None
        # 下一次动画路径上 cursor 文字滚动方向 ("up"/"down");
        # 默认 "up" (页码增大)
        self._next_text_direction: str = "up"

        # ---- UI ----
        self._build_ui()
        self._apply_disabled_state()

        # 首次构建 range
        self._rebuild_items()

        # 自动放置 cursor (首次 show 后)
        QTimer.singleShot(0, self._initial_cursor_position)

        # auto 主题
        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # UI 构建
    # ============================================================

    def _build_ui(self):
        """wrapper 是相对定位容器,cursor 是其子 widget,layout 排列 items。"""
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._wrapper = QWidget(self)
        outer.addWidget(self._wrapper, 0, Qt.AlignmentFlag.AlignLeft)

        self._items_layout = QHBoxLayout(self._wrapper)
        spacing = 0 if self._is_compact else PAGINATION_SIZES[self._size]["list_gap"]
        self._items_layout.setSpacing(spacing)
        self._items_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # 上下留 pad 给 cursor scale 1.1 扩张时不被 clip
        self._update_layout_margins()

        self._cursor = _CursorWidget(self._wrapper)
        self._cursor.hide()
        if not self._disable_cursor_animation:
            self._cursor_opacity_effect = QGraphicsOpacityEffect(self._cursor)
            self._cursor_opacity_effect.setOpacity(0.0)
            self._cursor.setGraphicsEffect(self._cursor_opacity_effect)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def _update_layout_margins(self):
        """根据当前 size 计算 cursor scale 所需的四周留白。"""
        cfg = PAGINATION_SIZES[self._size]
        scale_max = cfg["cursor_scale_max"]
        pad_h = max(2, int(cfg["item_height"] * (scale_max - 1.0) / 2) + 2)
        pad_w = max(2, int(cfg["item_height"] * (scale_max - 1.0) / 2) + 2)
        # 左右同样留 pad,避免首尾 item 上的 cursor 被 wrapper clip
        self._items_layout.setContentsMargins(pad_w, pad_h, pad_w, pad_h)

    # ============================================================
    # 静态校验
    # ============================================================

    @staticmethod
    def _validate(name: str, value, valid):
        if value not in valid:
            raise ValueError(f"{name} must be one of {tuple(valid)}, got {value!r}")

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # 公共 API: 翻页
    # ============================================================

    def total(self) -> int:
        return self._total

    def current_page(self) -> int:
        return self._active_page

    def set_page(self, page: int):
        """跳到指定页,触发 page_changed。"""
        target = max(1, min(int(page), self._total))
        if target == self._active_page:
            return
        old_page = self._active_page
        self._active_page = target
        # 记录本次切页的滚动方向:增大向上,减小向下
        self._next_text_direction = "up" if target > old_page else "down"
        self._rebuild_items()
        # 延到下一帧等 layout 稳定后再动 cursor,优先级高于 resizeEvent 的静态重定位
        self._schedule_cursor_move(animate=True)
        self.page_changed.emit(self._active_page)

    def go_next(self):
        if self._active_page == self._total:
            if self._loop:
                self.set_page(1)
            return
        self.set_page(self._active_page + 1)

    def go_previous(self):
        if self._active_page == 1:
            if self._loop:
                self.set_page(self._total)
            return
        self.set_page(self._active_page - 1)

    def go_first(self):
        self.set_page(1)

    def go_last(self):
        self.set_page(self._total)

    def set_total(self, total: int):
        t = max(1, int(total))
        if t == self._total:
            return
        self._total = t
        if self._active_page > t:
            self._active_page = t
        self._rebuild_items()
        self._move_cursor_to_active(animate=False)

    def set_dots_jump(self, n: int):
        self._dots_jump = max(1, int(n))

    def set_siblings(self, n: int):
        self._siblings = max(0, int(n))
        self._rebuild_items()
        self._move_cursor_to_active(animate=False)

    def set_boundaries(self, n: int):
        self._boundaries = max(0, int(n))
        self._rebuild_items()
        self._move_cursor_to_active(animate=False)

    # ============================================================
    # 公共 API: 视觉变体
    # ============================================================

    def set_variant(self, variant: str):
        self._validate("variant", variant, VALID_VARIANTS)
        self._variant = variant
        self._apply_state_to_items()
        self.update()

    def set_color(self, color: str):
        self._validate("color", color, VALID_COLORS)
        self._color = color
        self._apply_state_to_items()
        self._configure_cursor()

    def set_size(self, size: str):
        self._validate("size", size, VALID_SIZES)
        self._size = size
        spacing = 0 if self._is_compact else PAGINATION_SIZES[self._size]["list_gap"]
        self._items_layout.setSpacing(spacing)
        self._update_layout_margins()
        self._apply_state_to_items()
        self._reposition_cursor_async()

    def set_radius(self, radius: str):
        self._validate("radius", radius, VALID_RADII)
        self._radius = radius
        self._apply_state_to_items()
        self._configure_cursor()
        self._reposition_cursor_async()

    def set_compact(self, compact: bool):
        self._is_compact = bool(compact)
        spacing = 0 if self._is_compact else PAGINATION_SIZES[self._size]["list_gap"]
        self._items_layout.setSpacing(spacing)
        self._apply_state_to_items()
        self._reposition_cursor_async()

    def set_disabled(self, disabled: bool):
        self._is_disabled = bool(disabled)
        self._apply_disabled_state()

    def set_show_controls(self, show: bool):
        self._show_controls = bool(show)
        self._rebuild_items()
        self._move_cursor_to_active(animate=False)

    def set_loop(self, loop: bool):
        self._loop = bool(loop)
        self._update_prev_next_disabled()

    def set_disable_animation(self, disable: bool):
        self._disable_animation = bool(disable)
        self._disable_cursor_animation = self._disable_cursor_animation or disable
        self._apply_state_to_items()
        # cursor 停掉
        stop_tween(self, "_cursor_anim_runner")
        stop_tween(self, "_cursor_fade_runner")
        self._move_cursor_to_active(animate=False)

    def set_disable_cursor_animation(self, disable: bool):
        self._disable_cursor_animation = bool(disable) or self._disable_animation
        if self._disable_cursor_animation:
            self._cursor.hide()
        else:
            self._cursor.show()
        self._apply_state_to_items()
        self._move_cursor_to_active(animate=False)

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
        self._apply_state_to_items()
        self._configure_cursor()

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用钩子。"""
        self._theme = theme
        self._apply_state_to_items()
        self._configure_cursor()

    # ============================================================
    # range 重排 / 创建 items
    # ============================================================

    def _rebuild_items(self):
        """根据 active/total/siblings/boundaries 重新生成 item widgets。"""
        # 删旧 items 前先 clearFocus, 防 Qt 自动把焦点漂移到隔壁组件的 item
        # (那会触发隔壁 _PaginationItem.focusInEvent 显示焦点环)
        for it in self._items:
            if it.hasFocus():
                it.clearFocus()

        # 清掉旧 items (保留 cursor)
        for it in self._items:
            self._items_layout.removeWidget(it)
            it.setParent(None)
            it.deleteLater()
        self._items.clear()
        self._active_item = None

        rng = compute_pagination_range(
            total=self._total,
            active_page=self._active_page,
            siblings=self._siblings,
            boundaries=self._boundaries,
            show_controls=self._show_controls,
        )

        # 标记 dots 是否在 active 之前 (用于 ForwardIcon 方向)
        active_idx = -1
        for i, v in enumerate(rng):
            if isinstance(v, int) and v == self._active_page:
                active_idx = i
                break

        # 创建 items
        for i, v in enumerate(rng):
            if isinstance(v, int):
                item = _PaginationItem(
                    PaginationItemType.PAGE,
                    page=v,
                    parent=self._wrapper,
                )
                item.clicked.connect(
                    lambda _checked=False, p=v: self._on_page_clicked(p)
                )
                if v == self._active_page:
                    self._active_item = item
                    item.set_active(True)
                    if self._disable_cursor_animation:
                        item.set_show_active_fill(True)
            elif v == PaginationItemType.PREV:
                item = _PaginationItem(PaginationItemType.PREV, parent=self._wrapper)
                item.clicked.connect(lambda _=False: self.go_previous())
            elif v == PaginationItemType.NEXT:
                item = _PaginationItem(PaginationItemType.NEXT, parent=self._wrapper)
                item.clicked.connect(lambda _=False: self.go_next())
            elif v == PaginationItemType.DOTS:
                # 判断这是左侧 dots 还是右侧 dots
                is_before = active_idx == -1 or i < active_idx
                item = _PaginationItem(
                    PaginationItemType.DOTS,
                    is_before=is_before,
                    parent=self._wrapper,
                )
                jump = self._dots_jump
                if is_before:
                    item.clicked.connect(
                        lambda _=False, j=jump: self.set_page(
                            max(1, self._active_page - j)
                        )
                    )
                else:
                    item.clicked.connect(
                        lambda _=False, j=jump: self.set_page(
                            min(self._total, self._active_page + j)
                        )
                    )
            else:
                continue

            self._items_layout.addWidget(item)
            self._items.append(item)

        # 标记首/末位置 (compact 圆角剪裁)
        if self._items:
            self._items[0].set_position_flags(
                is_first=True, is_last=len(self._items) == 1
            )
            self._items[-1].set_position_flags(is_first=False, is_last=True)
            for it in self._items[1:-1]:
                it.set_position_flags(is_first=False, is_last=False)

        self._apply_state_to_items()
        self._update_prev_next_disabled()
        # cursor 配置 + 显示
        self._configure_cursor()
        # 新增 items 后,cursor 必须重新提到顶层 (浮层在 items 之上)
        if not self._disable_cursor_animation:
            self._cursor.raise_()

    def _apply_state_to_items(self):
        for it in self._items:
            it.apply_state(
                variant=self._variant,
                color=self._color,
                size=self._size,
                theme=self._theme,
                radius=self._radius,
                is_compact=self._is_compact,
                disable_animation=self._disable_animation,
            )
        # active item 单独打 show_active_fill (cursor 关闭模式)
        for it in self._items:
            is_active = (
                it.item_type() == PaginationItemType.PAGE
                and it.page() == self._active_page
            )
            it.set_active(is_active)
            it.set_show_active_fill(is_active and self._disable_cursor_animation)

    def _update_prev_next_disabled(self):
        """非 loop 时,prev/next 在边界禁用。"""
        for it in self._items:
            if it.item_type() == PaginationItemType.PREV:
                it.setEnabled(self._loop or self._active_page > 1)
            elif it.item_type() == PaginationItemType.NEXT:
                it.setEnabled(self._loop or self._active_page < self._total)

    def _on_page_clicked(self, page: int):
        if page == self._active_page:
            return
        self.set_page(page)

    # ============================================================
    # cursor 调度
    # ============================================================

    def _configure_cursor(self):
        """根据当前样式刷新 cursor 视觉参数。"""
        if self._disable_cursor_animation:
            self._cursor.hide()
            return
        cfg = PAGINATION_SIZES[self._size]
        radius_px = resolve_radius_px(self._radius, cfg["item_height"])
        self._cursor.configure(
            variant=self._variant,
            color=self._color,
            theme=self._theme,
            radius_px=radius_px,
            font_size=cfg["font_size"],
        )
        # 仅首次配置时给一个初始页码文本;后续切页由 _move_cursor_to_active
        # 独占管理 (静态硬切 / 动画交叉淡入),避免覆盖动画起始的旧文字
        if not self._cursor.has_page_text():
            self._cursor.set_page_text(str(self._active_page))

    def _initial_cursor_position(self):
        if self._disable_cursor_animation:
            return
        self._schedule_cursor_move(animate=False)

    def _schedule_cursor_move(self, animate: bool):
        """调度 cursor 移动,animate=True 优先级高于 False。"""
        if self._cursor_pending_animate is None:
            # 无 pending,新建
            self._cursor_pending_animate = animate
            QTimer.singleShot(0, self._flush_cursor_move)
        elif animate and not self._cursor_pending_animate:
            # 已有 False pending,升级为 True
            self._cursor_pending_animate = True

    def _flush_cursor_move(self):
        """执行 pending 的 cursor 移动。"""
        animate = self._cursor_pending_animate
        self._cursor_pending_animate = None
        if animate is None:
            return
        self._move_cursor_to_active(animate=animate)

    def _reposition_cursor_async(self):
        self._schedule_cursor_move(animate=False)

    def _find_active_item(self) -> Optional[_PaginationItem]:
        for it in self._items:
            if (
                it.item_type() == PaginationItemType.PAGE
                and it.page() == self._active_page
            ):
                return it
        return None

    def _move_cursor_to_active(self, *, animate: bool):
        """把 cursor 移到当前 active item 上。"""
        if self._disable_cursor_animation:
            return
        target = self._find_active_item()
        if target is None:
            self._cursor.hide()
            return

        # 强制 layout 完成 (不依赖 isVisible:刚 addWidget 的 widget visible 可能仍是 False)
        self._wrapper.layout().activate()
        item_geom = target.geometry()
        if item_geom.width() <= 0 or item_geom.height() <= 0:
            # layout 尚未完成,下一帧重试
            QTimer.singleShot(0, lambda: self._move_cursor_to_active(animate=animate))
            return

        cfg = PAGINATION_SIZES[self._size]
        scale_max = cfg["cursor_scale_max"]
        # cursor widget 比 item 大一圈,留 pad 容纳 1.1x scale 扩张
        pad_w = max(2, int(item_geom.width() * (scale_max - 1.0) / 2) + 2)
        pad_h = max(2, int(item_geom.height() * (scale_max - 1.0) / 2) + 2)
        cursor_geom = QRect(
            item_geom.x() - pad_w,
            item_geom.y() - pad_h,
            item_geom.width() + pad_w * 2,
            item_geom.height() + pad_h * 2,
        )

        # cursor paint 用 item 真实尺寸 (圆角与 item 完全贴合)
        self._cursor.set_item_size(item_geom.width(), item_geom.height())

        # 静态路径: 不动画 / 全禁用动画 / 首次显示
        if not animate or self._disable_animation or not self._cursor.isVisible():
            stop_tween(self, "_cursor_anim_runner")
            self._cursor.set_page_text(str(self._active_page))
            self._cursor.setGeometry(cursor_geom)
            self._cursor.set_scale(1.0)
            self._cursor.show()
            self._cursor.raise_()
            self._fade_in_cursor_if_needed()
            return

        # 动画路径: 文字方向化交叉滚动 (与 cursor 滑动同步,匹配阶段一时长)
        self._cursor.start_text_swap(
            str(self._active_page),
            duration_ms=cfg["cursor_anim_ms"],
            direction=self._next_text_direction,
        )

        # 两阶段动画 (对齐 HeroUI scrollTo): widget y/h/w 先到位, 只动画 x + scale
        start_x = float(self._cursor.x())
        end_x = float(cursor_geom.x())
        cursor_w = cursor_geom.width()
        cursor_y = cursor_geom.y()
        cursor_h = cursor_geom.height()

        self._cursor.setGeometry(int(start_x), cursor_y, cursor_w, cursor_h)
        self._cursor.raise_()

        def _on_step(x: float, scale: float):
            try:
                self._cursor.setGeometry(int(x), cursor_y, cursor_w, cursor_h)
                self._cursor.set_scale(scale)
            except RuntimeError:
                pass

        start_cursor_slide(
            self,
            "_cursor_anim_runner",
            start_x,
            end_x,
            _on_step,
            transition_ms=cfg["cursor_anim_ms"],
            max_scale=scale_max,
            easing=QEasingCurve.Type.OutCubic,
        )

    def _fade_in_cursor_if_needed(self):
        """首次显示 cursor 时淡入。"""
        if self._cursor_opacity_effect is None:
            return
        if not self._cursor_first_show:
            # 已经淡入过,直接保持 1.0
            self._cursor_opacity_effect.setOpacity(1.0)
            self._cursor.set_opacity(1.0)
            return
        self._cursor_first_show = False

        # 同时把 _CursorWidget 内部的 opacity 设 1 (paintEvent 用)
        self._cursor.set_opacity(1.0)

        if self._disable_animation:
            self._cursor_opacity_effect.setOpacity(1.0)
            return

        def _on_step(value):
            try:
                self._cursor_opacity_effect.setOpacity(float(value))
            except RuntimeError:
                pass

        tween_value(
            self,
            "_cursor_fade_runner",
            0.0,
            1.0,
            _on_step,
            duration=self.CURSOR_FADE_IN_MS,
        )

    # ============================================================
    # disabled 状态
    # ============================================================

    def _apply_disabled_state(self):
        if self._is_disabled:
            eff = QGraphicsOpacityEffect(self)
            eff.setOpacity(0.5)
            self.setGraphicsEffect(eff)
            self.setEnabled(False)
        else:
            self.setGraphicsEffect(None)
            self.setEnabled(True)

    # ============================================================
    # Qt 事件
    # ============================================================

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._reposition_cursor_async()

    def showEvent(self, ev):
        super().showEvent(ev)
        self._reposition_cursor_async()


__all__ = ["Pagination"]
