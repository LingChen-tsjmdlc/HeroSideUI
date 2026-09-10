"""
HeroSideUI Drawer Component
基于 HeroUI v2 设计风格，保持 PySide 原生 API

样式来源:
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/drawer.ts
    https://github.com/heroui-inc/heroui/blob/main/packages/core/theme/src/components/modal.ts
动效来源:
    https://github.com/heroui-inc/heroui/blob/main/packages/components/drawer/src/use-drawer.ts
文档参考: https://v2.heroui.com/docs/components/drawer

结构:
    Drawer (QWidget，作为 **宿主窗口的子 widget** 覆盖整个客户区；默认隐藏)
        └── _DrawerPanel (侧滑面板：QSS 背景 + 按 placement 削平的圆角)
                ├── content (对外内容容器，用户往里塞任意组件)
                └── close 按钮（右上角浮层，可自定义 / 隐藏）

    遮罩是 host 的另一个子 widget（_DrawerBackdrop，复用 Popover 的 _Backdrop），
    用 stackUnder 压在 Drawer 下面 —— 层级：host 内容 < 遮罩 < Drawer < 面板。
    绘制与模糊全部由 _Backdrop 负责，Drawer 自身不画东西，避免和 Button 自带的
    PressScaleEffect 抢 QGraphicsEffect。

    入场：面板从屏幕外滑到贴边位（200ms easeOut）+ 遮罩淡入
    出场：面板滑出屏幕（100ms easeIn）+ 遮罩淡出，结束才 hide()
    disable_animation=True 时直接跳到终态。
"""

from typing import Callable, Optional, Union
from weakref import WeakKeyDictionary, ref

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QWidget

from ...themes import (
    DRAWER_SIZES,
    DRAWER_SPEC,
    VALID_DRAWER_BACKDROPS,
    VALID_DRAWER_PLACEMENTS,
    VALID_DRAWER_RADII,
    VALID_DRAWER_SIZES,
)
from ...core import ThemeProvider
from ...utils import safe_delete
from ._backdrop import _DrawerBackdrop
from ._panel import _DrawerPanel


class Drawer(QWidget):
    """HeroUI 风格抽屉 — 侧滑面板 + 遮罩 + Esc 关闭。

    宿主窗口 = ``host``，未指定时取 ``parent`` 所在的顶层窗口（都没有则延迟到
    首次打开时取当前活动窗口）。内容一律通过 ``content_widget()`` 组装。

    常用参数：
        size                  - 十档字符串，或数字（px 强制滑出轴长度：
                                left/right 定宽，top/bottom 定高）
        radius/placement      - 视觉规格
        backdrop              - transparent / opaque / blur（默认 opaque）
        is_open               - 开合状态
        is_dismissable        - 点遮罩 / Esc 是否可关闭（默认 True）
        is_keyboard_dismiss_disabled - 单独禁掉 Esc（默认 False）
        hide_close_button / close_button - 关闭按钮的隐藏与自定义
        disable_animation     - 关闭滑入滑出（默认 False）
        on_open_change / on_close - 状态回调
    """

    open_changed = Signal(bool)
    closed = Signal()

    # 每个宿主窗口的开放抽屉栈（弱键 + 弱值引用）—— 只有栈顶启用 Esc，
    # 否则多个同键 QShortcut 同时启用会触发 Qt 二义性，Esc 一个都关不掉
    _open_drawers: "WeakKeyDictionary[QWidget, list]" = WeakKeyDictionary()

    def __init__(
        self,
        size: Union[str, int] = "md",
        radius: str = "lg",
        placement: str = "right",
        backdrop: str = "opaque",
        is_open: bool = False,
        is_dismissable: bool = True,
        is_keyboard_dismiss_disabled: bool = False,
        hide_close_button: bool = False,
        close_button: Optional[QWidget] = None,
        disable_animation: bool = False,
        on_open_change: Optional[Callable[[bool], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        host: Optional[QWidget] = None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        size = self._check_size(size)
        if radius not in VALID_DRAWER_RADII:
            raise ValueError(f"radius must be one of {VALID_DRAWER_RADII}, got {radius!r}")
        if placement not in VALID_DRAWER_PLACEMENTS:
            raise ValueError(
                f"placement must be one of {VALID_DRAWER_PLACEMENTS}, got {placement!r}"
            )
        if backdrop not in VALID_DRAWER_BACKDROPS:
            raise ValueError(
                f"backdrop must be one of {VALID_DRAWER_BACKDROPS}, got {backdrop!r}"
            )

        host_widget = host if host is not None else self._top_window(parent)
        super().__init__(host_widget)

        self._host: Optional[QWidget] = host_widget
        self._size: Union[str, int] = size
        self._radius = radius
        self._placement = placement
        self._backdrop_kind = backdrop
        self._backdrop: Optional[_DrawerBackdrop] = None
        self._is_open = False
        self._closing = False
        self._is_dismissable = bool(is_dismissable)
        self._is_keyboard_dismiss_disabled = bool(is_keyboard_dismiss_disabled)
        self._disable_animation = bool(disable_animation)
        self._on_open_change = on_open_change
        self._on_close = on_close
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

        # 关闭收尾计时器：等遮罩淡出走完再 hide()，避免遮罩被硬切掉
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._finish_close)

        self._panel = _DrawerPanel(self._theme, parent=self)
        self._panel.close_requested.connect(lambda: self.set_is_open(False))
        self._panel.set_hide_close_button(hide_close_button)
        if close_button is not None:
            self._panel.set_close_button(close_button)
        self._slide_anim = QPropertyAnimation(self._panel, b"pos", self)

        # Esc —— 仅在打开且允许键盘关闭时启用
        self._esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._esc.setContext(Qt.ShortcutContext.WindowShortcut)
        self._esc.setEnabled(False)
        self._esc.activated.connect(self._on_escape)

        if self._host is not None:
            self._host.installEventFilter(self)

        self._apply_style()

        if theme == "auto":
            ThemeProvider.instance().register(self)

        if is_open:
            self.set_is_open(True)

    # ============================================================
    # 校验
    # ============================================================
    @staticmethod
    def _check_size(size: Union[str, int]) -> Union[str, int]:
        """校验 size —— 十档字符串，或正数（px，作用在滑出轴上）。"""
        if isinstance(size, bool) or not isinstance(size, (str, int, float)):
            raise ValueError(
                f"size must be one of {VALID_DRAWER_SIZES} or a positive number, "
                f"got {size!r}"
            )
        if isinstance(size, (int, float)):
            px = int(size)
            if px <= 0:
                raise ValueError(f"numeric size must be > 0, got {size!r}")
            return px
        if size not in VALID_DRAWER_SIZES:
            raise ValueError(
                f"size must be one of {VALID_DRAWER_SIZES} or a positive number, "
                f"got {size!r}"
            )
        return size

    # ============================================================
    # 遮罩
    # ============================================================
    def _is_top_open(self) -> bool:
        """自己是否是宿主上最顶层的开放抽屉（决定 Esc 归属）。"""
        if self._host is None:
            return False
        stack = Drawer._open_drawers.get(self._host) or []
        live = [r() for r in stack if r() is not None]
        return bool(live) and live[-1] is self

    def _register_open(self):
        """入栈并按栈同步 Esc 启用状态（栈顶才启用）。"""
        if self._host is None:
            return
        stack = Drawer._open_drawers.setdefault(self._host, [])
        stack[:] = [r for r in stack if r() is not None and r() is not self]  # 防关闭途中重开重复入栈
        stack.append(ref(self))
        for d in (r() for r in stack):
            if d is not None:
                d._esc.setEnabled(d is self and d._dismissable_by_key())

    def _unregister_open(self):
        """出栈并把 Esc 归还给新的栈顶。"""
        if self._host is None:
            return
        stack = Drawer._open_drawers.get(self._host)
        if stack is not None:
            stack[:] = [r for r in stack if r() is not None and r() is not self]
        for d in (r() for r in (Drawer._open_drawers.get(self._host) or [])):
            if d is not None:
                d._esc.setEnabled(d._is_top_open() and d._dismissable_by_key())

    def _create_backdrop(self):
        """建遮罩 —— 必须在 Drawer 自己 show() 之前调，否则 blur 快照会拍进面板。"""
        if self._backdrop_kind == "transparent" or self._host is None:
            return
        # 先把自己顶到兄弟层最上方：Drawer 若还压在 centralWidget 之下，
        # stackUnder 以它为锚点会把遮罩也压到内容之下（首次打开踩过）
        self.raise_()
        bd = _DrawerBackdrop(self._backdrop_kind, host=self._host)
        bd.setGeometry(0, 0, self._host.width(), self._host.height())
        if self._backdrop_kind == "blur":
            bd.prepare_blur_snapshot()
        bd.show()
        bd.stackUnder(self)  # host 内容之上、Drawer 之下
        if self._disable_animation:
            bd.settle(1.0)
        else:
            bd.play_in()
        self._backdrop = bd

    def _destroy_backdrop(self):
        if self._backdrop is None:
            return
        safe_delete(self._backdrop)
        self._backdrop = None

    def _rebuild_backdrop(self):
        """换遮罩 —— 先藏自己再抓快照，避免把面板拍进 blur 底图。"""
        self._destroy_backdrop()
        self.hide()
        self._create_backdrop()
        self.show()
        self.raise_()
        self._panel.show()
        self._panel.raise_()

    # ============================================================
    # 几何
    # ============================================================
    def _axis_limit(self) -> int:
        """滑出轴上的长度上限；<=0 表示铺满宿主。"""
        if isinstance(self._size, str):
            if self._size == "full":
                return 0
            cfg = DRAWER_SIZES.get(self._size, DRAWER_SIZES["md"])
            return cfg["max_w"] if self._is_horizontal() else cfg["max_h"]
        return int(self._size)

    def _is_horizontal(self) -> bool:
        """滑出轴是否水平（left / right 沿 x 滑，宽度受 size 约束）。"""
        return self._placement in ("left", "right")

    def _min_slide(self) -> int:
        """上下抽屉空内容时的高度兜底（padding×2 + 关闭按钮）。"""
        return DRAWER_SPEC["padding"] * 2 + DRAWER_SPEC["close_size"]

    def _panel_rect(self) -> QRect:
        """面板的贴边终态几何。

        贴边轴始终铺满宿主（官方 inset-y-0 / inset-x-0）。
        档位 size：左右抽屉宽度固定为档位（官方 max-w 语义）；
        上下抽屉高度内容自适应 min(内容 sizeHint, 档位上限, 宿主高)，
        空内容兜底 _min_slide()（官方 max-h 只封顶不托底）。
        数字 size 强制控制滑出轴长度（不看内容，超宿主钳制）；
        full（上限<=0）铺满。
        """
        area = self.rect()
        limit = self._axis_limit()
        if self._is_horizontal():
            w = area.width() if limit <= 0 else min(limit, area.width())
            x = 0 if self._placement == "left" else area.width() - w
            return QRect(x, 0, w, area.height())
        if limit <= 0:
            h = area.height()
        elif isinstance(self._size, int):
            h = min(limit, area.height())  # 数字强制定高，不看内容
        else:
            h = max(
                self._min_slide(),
                min(self._panel.sizeHint().height(), limit, area.height()),
            )
        y = 0 if self._placement == "top" else area.height() - h
        return QRect(0, y, area.width(), h)

    def _hidden_rect(self, target: QRect) -> QRect:
        """面板完全滑出宿主可视区的几何（退场终点 / 入场起点）。"""
        area = self.rect()
        if self._placement == "left":
            return QRect(-target.width(), 0, target.width(), target.height())
        if self._placement == "right":
            return QRect(area.width(), 0, target.width(), target.height())
        if self._placement == "top":
            return QRect(0, -target.height(), target.width(), target.height())
        return QRect(0, area.height(), target.width(), target.height())

    def _sync_geometry(self):
        """跟随宿主客户区尺寸。"""
        if self._host is None:
            return
        self.setGeometry(self._host.rect())

    def _reposition(self):
        """规格 / 宿主尺寸变化后把面板摆回贴边位（不动画）。"""
        if not self._is_open or self._host is None:
            return
        self._slide_anim.stop()
        self._panel.setGeometry(self._panel_rect())

    # ============================================================
    # 开合
    # ============================================================
    def _open(self):
        if self._host is None:
            self._bind_host(self._top_window(None))
        if self._host is None:
            raise ValueError("Drawer 需要宿主窗口：构造时传 host= 或 parent=")

        self._close_timer.stop()
        self._slide_anim.stop()
        self._destroy_backdrop()
        self._is_open = True
        self._closing = False

        self._sync_geometry()
        target = self._panel_rect()
        self._panel.setGeometry(
            target if self._disable_animation else self._hidden_rect(target)
        )
        self.hide()  # 保证 blur 快照拍不到面板（关闭途中重开时自己还是可见的）
        self._create_backdrop()
        self.show()
        self.raise_()
        self._panel.show()
        self._panel.raise_()
        self._esc.setEnabled(self._dismissable_by_key())
        self._register_open()

        if self._disable_animation:
            self._panel.move(target.topLeft())
        else:
            self._slide_to(target.topLeft(), DRAWER_SPEC["duration_enter"], True)

        self._emit_open_changed(True)

    def _close(self):
        self._is_open = False
        self._esc.setEnabled(False)
        if self._disable_animation:
            self._closing = False
            self._finish_close()
            return
        self._closing = True
        hidden = self._hidden_rect(self._panel.geometry())
        self._slide_to(hidden.topLeft(), DRAWER_SPEC["duration_exit"], False)
        # 等遮罩淡出走完再收尾；没有遮罩时按侧滑时长收尾
        if self._backdrop is not None:
            self._backdrop.play_out()
            self._close_timer.start(DRAWER_SPEC["duration_backdrop_out"])
        else:
            self._close_timer.start(DRAWER_SPEC["duration_exit"])

    def _finish_close(self):
        if self._is_open:
            return  # 关闭途中又被打开
        self._closing = False
        self._close_timer.stop()
        self._slide_anim.stop()
        self._destroy_backdrop()
        self.hide()
        self._unregister_open()
        self._emit_open_changed(False)
        self.closed.emit()
        if self._on_close is not None:
            self._on_close()

    def _emit_open_changed(self, opened: bool):
        self.open_changed.emit(opened)
        if self._on_open_change is not None:
            self._on_open_change(opened)

    def _slide_to(self, end: QPoint, duration: int, entering: bool):
        """面板位移动画；entering 用 easeOut，退场用 easeIn（use-drawer.ts）。"""
        self._slide_anim.stop()
        self._slide_anim.setDuration(max(0, duration))
        self._slide_anim.setEasingCurve(
            QEasingCurve.Type.OutCubic if entering else QEasingCurve.Type.InCubic
        )
        self._slide_anim.setStartValue(QPoint(self._panel.pos()))
        self._slide_anim.setEndValue(QPoint(end))
        self._slide_anim.start()

    # ============================================================
    # 事件
    # ============================================================
    def _on_escape(self):
        if self._is_open and self._dismissable_by_key():
            self.set_is_open(False)

    def mousePressEvent(self, event):
        # 只有点在遮罩区（面板之外）才关闭；面板上的点击照常交给子控件
        if (
            self._is_open
            and self._is_dismissable
            and event.button() == Qt.MouseButton.LeftButton
            and not self._panel.geometry().contains(event.position().toPoint())
        ):
            self.set_is_open(False)
            event.accept()
            return
        super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        if obj is self._host and event.type() == QEvent.Type.Resize:
            self._sync_geometry()
            self._reposition()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if self._host is not None:
            try:
                self._host.removeEventFilter(self)
            except RuntimeError:
                pass
        super().closeEvent(event)

    # ============================================================
    # 宿主
    # ============================================================
    @staticmethod
    def _top_window(widget: Optional[QWidget]) -> Optional[QWidget]:
        if widget is None:
            app = QApplication.instance()
            return app.activeWindow() if app is not None else None
        return widget.window()

    def _bind_host(self, host: Optional[QWidget]):
        """切换宿主：挪走 eventFilter 并重新挂父。"""
        if host is None or host is self._host:
            return
        if self._host is not None:
            try:
                self._host.removeEventFilter(self)
            except RuntimeError:
                pass
        self._host = host
        self.setParent(host)
        host.installEventFilter(self)
        if self._is_open:
            self._unregister_open()  # 换宿主前先从旧宿主的开放栈退出
            # 换父会把 widget 变隐藏 —— 正好趁这时候重抓 blur 快照，再重新显示
            self._destroy_backdrop()
            self._create_backdrop()
            self.show()
            self.raise_()
            self._panel.show()
            self._panel.raise_()
            self._register_open()

    def set_host(self, host: Optional[QWidget]):
        """更换被覆盖的宿主窗口。"""
        self._bind_host(host)
        self._sync_geometry()
        self._reposition()

    def host(self) -> Optional[QWidget]:
        return self._host

    # ============================================================
    # 内容
    # ============================================================
    def content_widget(self) -> QWidget:
        """内容容器 —— 用户往它的 layout 里添加任意组件。"""
        return self._panel.content_widget()

    def add_widget(self, widget: QWidget):
        """向内容容器追加组件；已打开时自适应几何即时重排。"""
        self._panel.add_widget(widget)
        self._reposition()

    def set_content(self, widget: Optional[QWidget]):
        """用单个组件替换全部内容；已打开时自适应几何即时重排。"""
        self._panel.set_content(widget)
        self._reposition()

    def clear_content(self):
        """清空内容容器；已打开时自适应几何即时重排。"""
        self._panel.clear_content()
        self._reposition()

    # ============================================================
    # 样式
    # ============================================================
    def _apply_style(self):
        self._panel.apply_style(self._radius, self._placement, self._size == "full")

    def _dismissable_by_key(self) -> bool:
        return self._is_dismissable and not self._is_keyboard_dismiss_disabled

    # ============================================================
    # 公共 API
    # ============================================================
    def is_open(self) -> bool:
        return self._is_open

    def set_is_open(self, value: bool):
        """开合抽屉 —— 会触发 open_changed / closed 与对应回调。"""
        value = bool(value)
        if value == self._is_open and not self._closing:
            return
        if value:
            self._open()
        else:
            self._close()

    def toggle(self):
        self.set_is_open(not self._is_open)

    def open_drawer(self):
        self.set_is_open(True)

    def close_drawer(self):
        self.set_is_open(False)

    def set_size(self, size: Union[str, int]):
        """改 size —— 十档字符串，或数字（px 强制滑出轴长度，不看内容）。"""
        self._size = self._check_size(size)
        self._apply_style()
        self._reposition()

    def set_radius(self, radius: str):
        if radius not in VALID_DRAWER_RADII:
            raise ValueError(f"radius must be one of {VALID_DRAWER_RADII}, got {radius!r}")
        self._radius = radius
        self._apply_style()

    def set_placement(self, placement: str):
        if placement not in VALID_DRAWER_PLACEMENTS:
            raise ValueError(
                f"placement must be one of {VALID_DRAWER_PLACEMENTS}, got {placement!r}"
            )
        self._placement = placement
        self._apply_style()
        self._reposition()

    def set_backdrop(self, backdrop: str):
        """改遮罩：transparent / opaque / blur；已打开会立刻换掉。"""
        if backdrop not in VALID_DRAWER_BACKDROPS:
            raise ValueError(
                f"backdrop must be one of {VALID_DRAWER_BACKDROPS}, got {backdrop!r}"
            )
        if backdrop == self._backdrop_kind:
            return
        self._backdrop_kind = backdrop
        if self._is_open:
            self._rebuild_backdrop()

    def set_is_dismissable(self, value: bool):
        self._is_dismissable = bool(value)
        self._esc.setEnabled(self._is_open and self._is_top_open() and self._dismissable_by_key())

    def set_is_keyboard_dismiss_disabled(self, value: bool):
        self._is_keyboard_dismiss_disabled = bool(value)
        self._esc.setEnabled(self._is_open and self._is_top_open() and self._dismissable_by_key())

    def set_hide_close_button(self, value: bool):
        self._panel.set_hide_close_button(value)

    def set_close_button(self, widget: Optional[QWidget]):
        """自定义关闭按钮（传 None 恢复内置按钮）。"""
        self._panel.set_close_button(widget)

    def set_disable_animation(self, value: bool):
        self._disable_animation = bool(value)

    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._panel.set_theme(self._theme)

    def _apply_provider_theme(self, theme: str):
        """ThemeProvider 广播专用 —— 只改色，不重复注册。"""
        self._theme = theme
        self._panel.apply_provider_theme(theme)

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ---- 只读访问器 ----
    def size(self) -> Union[str, int]:
        return self._size

    def radius(self) -> str:
        return self._radius

    def placement(self) -> str:
        return self._placement

    def backdrop(self) -> str:
        return self._backdrop_kind

    def is_dismissable(self) -> bool:
        return self._is_dismissable

    def is_keyboard_dismiss_disabled(self) -> bool:
        return self._is_keyboard_dismiss_disabled

    def disable_animation(self) -> bool:
        return self._disable_animation
