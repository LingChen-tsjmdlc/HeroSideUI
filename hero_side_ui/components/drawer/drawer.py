"""Drawer 组件：侧滑面板 + 遮罩 + Esc 关闭（HeroUI v2 风格）。

层级：宿主内容 < 遮罩(复用 Popover _Backdrop) < Drawer < 面板；入场滑入
200ms + 遮罩淡入，出场 100ms 滑出后 hide()。
"""

from collections.abc import Callable
from typing import ClassVar
from weakref import WeakKeyDictionary, ref

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QWidget

from ...animation import stop_tween, tween_property
from ...core import ThemeProvider
from ...themes import (
    DRAWER_SIZES,
    DRAWER_SPEC,
    VALID_DRAWER_BACKDROPS,
    VALID_DRAWER_PLACEMENTS,
    VALID_DRAWER_RADII,
    VALID_DRAWER_SIZES,
)
from ...utils import safe_delete
from ._backdrop import _DrawerBackdrop
from ._panel import _DrawerPanel


class Drawer(QWidget):
    """HeroUI 风格抽屉 — 侧滑面板 + 遮罩 + Esc 关闭。

    Note:
        宿主未指定时取 parent 顶层窗口，再延迟到首次打开取活动窗口；
        size 支持十档字符串或数字 px（强制滑出轴长度）；内容经
        content_widget() 组装。
    """

    open_changed = Signal(bool)
    closed = Signal()

    # 每个宿主窗口的开放抽屉栈（弱键 + 弱值引用）—— 只有栈顶启用 Esc，
    # 否则多个同键 QShortcut 同时启用会触发 Qt 二义性，Esc 一个都关不掉
    _open_drawers: ClassVar["WeakKeyDictionary[QWidget, list]"] = WeakKeyDictionary()

    def __init__(
        self,
        size: str | int = "md",
        radius: str = "lg",
        placement: str = "right",
        backdrop: str = "opaque",
        is_open: bool = False,
        is_dismissable: bool = True,
        is_keyboard_dismiss_disabled: bool = False,
        hide_close_button: bool = False,
        close_button: QWidget | None = None,
        disable_animation: bool = False,
        on_open_change: Callable[[bool], None] | None = None,
        on_close: Callable[[], None] | None = None,
        host: QWidget | None = None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建抽屉：遮罩 + 侧滑面板 + Esc 关闭。

        Args:
            size: 尺寸档位字符串或数字 px（强制滑出轴长度）。
            radius: 圆角档位。
            placement: 贴边方向 left / right / top / bottom。
            backdrop: transparent / opaque / blur。
            is_open: 构造后立即打开。
            is_dismissable: 点遮罩是否可关闭。
            is_keyboard_dismiss_disabled: 是否禁用 Esc 关闭。
            hide_close_button: 隐藏内置关闭按钮。
            close_button: 自定义关闭按钮 widget。
            disable_animation: 关闭滑入滑出与遮罩淡入淡出。
            on_open_change: 开合状态回调 fn(bool)。
            on_close: 完全关闭后的回调。
            host: 被覆盖的宿主窗口；None 时取 parent 顶层窗口。
            theme: auto / light / dark。
            parent: Qt 父对象。

        Raises:
            ValueError: radius / placement / backdrop / size 非法时抛出。

        Note:
            开放抽屉按宿主窗口维护弱引用栈，只有栈顶启用 Esc，
            避免多个同键 QShortcut 同时启用触发 Qt 二义性。
        """
        size = self._check_size(size)
        if radius not in VALID_DRAWER_RADII:
            raise ValueError(f"radius must be one of {VALID_DRAWER_RADII}, got {radius!r}")
        if placement not in VALID_DRAWER_PLACEMENTS:
            raise ValueError(
                f"placement must be one of {VALID_DRAWER_PLACEMENTS}, got {placement!r}"
            )
        if backdrop not in VALID_DRAWER_BACKDROPS:
            raise ValueError(f"backdrop must be one of {VALID_DRAWER_BACKDROPS}, got {backdrop!r}")

        host_widget = host if host is not None else self._top_window(parent)
        super().__init__(host_widget)

        self._host: QWidget | None = host_widget
        self._size: str | int = size
        self._radius = radius
        self._placement = placement
        self._backdrop_kind = backdrop
        self._backdrop: _DrawerBackdrop | None = None
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
        self._slide_anim = None

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
    def _check_size(size: str | int) -> str | int:
        """校验并归一化 size。

        Args:
            size: 十档字符串，或正数（px，作用在滑出轴上）。

        Returns:
            合法字符串原样返回；数字转为正 int。

        Raises:
            ValueError: 类型不符、数字 <= 0 或字符串不在合法集合时抛出。
        """
        if isinstance(size, bool) or not isinstance(size, (str, int, float)):
            raise ValueError(
                f"size must be one of {VALID_DRAWER_SIZES} or a positive number, got {size!r}"
            )
        if isinstance(size, (int, float)):
            px = int(size)
            if px <= 0:
                raise ValueError(f"numeric size must be > 0, got {size!r}")
            return px
        if size not in VALID_DRAWER_SIZES:
            raise ValueError(
                f"size must be one of {VALID_DRAWER_SIZES} or a positive number, got {size!r}"
            )
        return size

    # ============================================================
    # 遮罩
    # ============================================================
    def _is_top_open(self) -> bool:
        """自己是否是宿主上最顶层的开放抽屉（决定 Esc 归属）。

        Returns:
            活引用栈末位是自己时为 True。
        """
        if self._host is None:
            return False
        stack = Drawer._open_drawers.get(self._host) or []
        live = [r() for r in stack if r() is not None]
        return bool(live) and live[-1] is self

    def _register_open(self):
        """入栈并按栈同步 Esc 启用状态（栈顶才启用）。

        Note:
            先剔除自己与已失效的弱引用，防止关闭途中重开重复入栈。
        """
        if self._host is None:
            return
        stack = Drawer._open_drawers.setdefault(self._host, [])
        stack[:] = [
            r for r in stack if r() is not None and r() is not self
        ]  # 防关闭途中重开重复入栈
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
        """建遮罩并播放淡入。

        Note:
            必须在 Drawer 自己 show() 之前调用，否则 blur 快照会拍进面板；
            先 raise_() 把自己顶到兄弟层最上方，否则 stackUnder 以它为
            锚点会把遮罩也压到 host 内容之下。
        """
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
        """销毁当前遮罩（safe_delete 延迟删除）。"""
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
        """滑出轴上的长度上限。

        Returns:
            <=0 表示铺满宿主；否则为档位 token 或数字 px 换算的长度。
        """
        if isinstance(self._size, str):
            if self._size == "full":
                return 0
            cfg = DRAWER_SIZES.get(self._size, DRAWER_SIZES["md"])
            return cfg["max_w"] if self._is_horizontal() else cfg["max_h"]
        return int(self._size)

    def _is_horizontal(self) -> bool:
        """滑出轴是否水平。

        Returns:
            left / right 沿 x 滑（宽度受 size 约束）时为 True。
        """
        return self._placement in ("left", "right")

    def _min_slide(self) -> int:
        """上下抽屉空内容时的高度兜底。

        Returns:
            padding×2 + 关闭按钮尺寸。
        """
        return DRAWER_SPEC["padding"] * 2 + DRAWER_SPEC["close_size"]

    def _panel_rect(self) -> QRect:
        """取面板贴边终态几何。

        Returns:
            面板 QRect：左右抽屉定宽，上下抽屉按内容自适应并以档位封顶。
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
        """面板完全滑出宿主可视区的几何（退场终点 / 入场起点）。

        Args:
            target: 面板贴边终态几何。

        Returns:
            沿 placement 反方向整体移出一屏的 QRect。
        """
        area = self.rect()
        if self._placement == "left":
            return QRect(-target.width(), 0, target.width(), target.height())
        if self._placement == "right":
            return QRect(area.width(), 0, target.width(), target.height())
        if self._placement == "top":
            return QRect(0, -target.height(), target.width(), target.height())
        return QRect(0, area.height(), target.width(), target.height())

    def _sync_geometry(self):
        """跟随宿主客户区尺寸铺满整个 Drawer。"""
        if self._host is None:
            return
        self.setGeometry(self._host.rect())

    def _reposition(self):
        """规格 / 宿主尺寸变化后把面板摆回贴边位（不动画）。"""
        if not self._is_open or self._host is None:
            return
        stop_tween(self, "_slide_anim")
        self._panel.setGeometry(self._panel_rect())

    # ============================================================
    # 开合
    # ============================================================
    def _open(self):
        """执行打开：同步几何、建遮罩、入栈、播放滑入。

        Raises:
            ValueError: 无宿主窗口且找不到活动窗口时抛出。

        Note:
            先 hide() 自己再建遮罩，保证 blur 快照拍不到面板
            （关闭途中重开时自己仍是可见的）。
        """
        if self._host is None:
            self._bind_host(self._top_window(None))
        if self._host is None:
            raise ValueError("Drawer 需要宿主窗口：构造时传 host= 或 parent=")

        self._close_timer.stop()
        stop_tween(self, "_slide_anim")
        self._destroy_backdrop()
        self._is_open = True
        self._closing = False

        self._sync_geometry()
        target = self._panel_rect()
        self._panel.setGeometry(target if self._disable_animation else self._hidden_rect(target))
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
        """执行关闭：播放滑出与遮罩淡出，计时结束后收尾。

        Note:
            禁用动画时直接走 _finish_close；有遮罩按遮罩淡出时长收尾，
            否则按侧滑时长收尾。
        """
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
        """关闭收尾：销毁遮罩、hide、出栈、发信号与回调。

        Note:
            关闭途中又被打开（_is_open 为 True）时直接返回，不做收尾。
        """
        if self._is_open:
            return  # 关闭途中又被打开
        self._closing = False
        self._close_timer.stop()
        stop_tween(self, "_slide_anim")
        self._destroy_backdrop()
        self.hide()
        self._unregister_open()
        self._emit_open_changed(False)
        self.closed.emit()
        if self._on_close is not None:
            self._on_close()

    def _emit_open_changed(self, opened: bool):
        """发出 open_changed 信号并触发 on_open_change 回调。

        Args:
            opened: True 表示已打开。
        """
        self.open_changed.emit(opened)
        if self._on_open_change is not None:
            self._on_open_change(opened)

    def _slide_to(self, end: QPoint, duration: int, entering: bool):
        """播放面板位移动画。

        Args:
            end: 目标左上角坐标。
            duration: 时长（毫秒）。
            entering: True 用 OutCubic、False 用 InCubic。

        Note:
            owner=self 让补间随 Drawer 生命周期管理，不会挂在面板上丢失。
        """
        tween_property(
            self._panel,
            "_slide_anim",
            b"pos",
            QPoint(end),
            owner=self,
            duration=max(0, duration),
            easing=QEasingCurve.Type.OutCubic if entering else QEasingCurve.Type.InCubic,
        )

    # ============================================================
    # 事件
    # ============================================================
    def _on_escape(self):
        """Esc 快捷键：打开且允许键盘关闭时收起抽屉。"""
        if self._is_open and self._dismissable_by_key():
            self.set_is_open(False)

    def mousePressEvent(self, event):
        """点击遮罩区（面板之外）时关闭抽屉。

        Args:
            event: Qt 鼠标按下事件。

        Note:
            面板上的点击照常交给子控件，不拦截。
        """
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
        """监听宿主 Resize：同步几何并把面板摆回贴边位。

        Args:
            obj: 被监听对象（宿主窗口）。
            event: 当前事件。

        Returns:
            一律交回父类。
        """
        if obj is self._host and event.type() == QEvent.Type.Resize:
            self._sync_geometry()
            self._reposition()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """组件关闭时从宿主摘掉事件过滤器。

        Args:
            event: Qt 关闭事件。
        """
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
    def _top_window(widget: QWidget | None) -> QWidget | None:
        """解析宿主顶层窗口。

        Args:
            widget: 参考 widget；None 时取当前活动窗口。

        Returns:
            顶层窗口；无 QApplication 或无活动窗口时为 None。
        """
        if widget is None:
            app = QApplication.instance()
            return app.activeWindow() if app is not None else None
        return widget.window()

    def _bind_host(self, host: QWidget | None):
        """切换宿主：挪走 eventFilter 并重新挂父。

        Args:
            host: 新宿主；None 或同值直接返回。

        Note:
            换父会把 widget 变隐藏，正好趁这时候重抓 blur 快照；
            打开状态下需先从旧宿主开放栈退出再重新入栈。
        """
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

    def set_host(self, host: QWidget | None):
        """更换被覆盖的宿主窗口并同步几何。

        Args:
            host: 新宿主窗口。
        """
        self._bind_host(host)
        self._sync_geometry()
        self._reposition()

    def host(self) -> QWidget | None:
        """返回当前宿主窗口。

        Returns:
            宿主 QWidget；尚未绑定时为 None。
        """
        return self._host

    # ============================================================
    # 内容
    # ============================================================
    def content_widget(self) -> QWidget:
        """内容容器。

        Returns:
            用户应把自定义组件加进其 layout 的 QWidget。
        """
        return self._panel.content_widget()

    def add_widget(self, widget: QWidget):
        """向内容容器追加组件；已打开时自适应几何即时重排。

        Args:
            widget: 待追加的 QWidget。
        """
        self._panel.add_widget(widget)
        self._reposition()

    def set_content(self, widget: QWidget | None):
        """用单个组件替换全部内容；已打开时自适应几何即时重排。

        Args:
            widget: 新内容；None 只清空。
        """
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
        """按当前 radius / placement / size 刷新面板外观。"""
        self._panel.apply_style(self._radius, self._placement, self._size == "full")

    def _dismissable_by_key(self) -> bool:
        """是否允许 Esc 关闭。

        Returns:
            dismissable 且未禁用键盘关闭时为 True。
        """
        return self._is_dismissable and not self._is_keyboard_dismiss_disabled

    # ============================================================
    # 公共 API
    # ============================================================
    def is_open(self) -> bool:
        """返回抽屉是否处于打开状态。

        Returns:
            True 表示已打开（含正在滑入）。
        """
        return self._is_open

    def set_is_open(self, value: bool):
        """开合抽屉 —— 会触发 open_changed / closed 与对应回调。

        Args:
            value: True 打开、False 关闭。

        Note:
            同值且未在关闭途中直接返回；关闭途中重新打开会中断收尾。
        """
        value = bool(value)
        if value == self._is_open and not self._closing:
            return
        if value:
            self._open()
        else:
            self._close()

    def toggle(self):
        """按当前状态切换开 / 关。"""
        self.set_is_open(not self._is_open)

    def open_drawer(self):
        """便捷接口：打开抽屉。"""
        self.set_is_open(True)

    def close_drawer(self):
        """便捷接口：关闭抽屉。"""
        self.set_is_open(False)

    def set_size(self, size: str | int):
        """改 size —— 十档字符串，或数字（px 强制滑出轴长度，不看内容）。

        Args:
            size: 新尺寸档位或像素值。

        Raises:
            ValueError: 非法值时由 _check_size 抛出。
        """
        self._size = self._check_size(size)
        self._apply_style()
        self._reposition()

    def set_radius(self, radius: str):
        """切换圆角档位并刷新外观。

        Args:
            radius: 圆角档位名。

        Raises:
            ValueError: 不在 VALID_DRAWER_RADII 中时抛出。
        """
        if radius not in VALID_DRAWER_RADII:
            raise ValueError(f"radius must be one of {VALID_DRAWER_RADII}, got {radius!r}")
        self._radius = radius
        self._apply_style()

    def set_placement(self, placement: str):
        """切换贴边方向并重摆面板。

        Args:
            placement: left / right / top / bottom。

        Raises:
            ValueError: 不在 VALID_DRAWER_PLACEMENTS 中时抛出。
        """
        if placement not in VALID_DRAWER_PLACEMENTS:
            raise ValueError(
                f"placement must be one of {VALID_DRAWER_PLACEMENTS}, got {placement!r}"
            )
        self._placement = placement
        self._apply_style()
        self._reposition()

    def set_backdrop(self, backdrop: str):
        """改遮罩：transparent / opaque / blur；已打开会立刻换掉。

        Args:
            backdrop: 新遮罩类型。

        Raises:
            ValueError: 不在 VALID_DRAWER_BACKDROPS 中时抛出。
        """
        if backdrop not in VALID_DRAWER_BACKDROPS:
            raise ValueError(f"backdrop must be one of {VALID_DRAWER_BACKDROPS}, got {backdrop!r}")
        if backdrop == self._backdrop_kind:
            return
        self._backdrop_kind = backdrop
        if self._is_open:
            self._rebuild_backdrop()

    def set_is_dismissable(self, value: bool):
        """切换点击遮罩是否可关闭，并同步 Esc 启用态。

        Args:
            value: True 允许点遮罩关闭。
        """
        self._is_dismissable = bool(value)
        self._esc.setEnabled(self._is_open and self._is_top_open() and self._dismissable_by_key())

    def set_is_keyboard_dismiss_disabled(self, value: bool):
        """切换是否禁用 Esc 关闭，并同步 Esc 启用态。

        Args:
            value: True 禁用键盘关闭。
        """
        self._is_keyboard_dismiss_disabled = bool(value)
        self._esc.setEnabled(self._is_open and self._is_top_open() and self._dismissable_by_key())

    def set_hide_close_button(self, value: bool):
        """切换内置关闭按钮显隐。

        Args:
            value: True 隐藏。
        """
        self._panel.set_hide_close_button(value)

    def set_close_button(self, widget: QWidget | None):
        """自定义关闭按钮。

        Args:
            widget: 新按钮；None 恢复内置按钮。
        """
        self._panel.set_close_button(widget)

    def set_disable_animation(self, value: bool):
        """切换是否关闭滑入滑出动画。

        Args:
            value: True 关闭动画。
        """
        self._disable_animation = bool(value)

    def set_theme(self, theme: str):
        """切换主题，并维护 ThemeProvider 注册状态。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
        """
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
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口只改色，不重复注册、不改 _theme_mode。
        """
        self._theme = theme
        self._panel.apply_provider_theme(theme)

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark / auto。

        Returns:
            light / dark 原样返回；其余取 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ---- 只读访问器 ----
    def size(self) -> str | int:
        """返回当前尺寸档位或像素值。

        Returns:
            size 字符串或 int px。
        """
        return self._size

    def radius(self) -> str:
        """返回当前圆角档位。

        Returns:
            圆角档位名。
        """
        return self._radius

    def placement(self) -> str:
        """返回当前贴边方向。

        Returns:
            left / right / top / bottom。
        """
        return self._placement

    def backdrop(self) -> str:
        """返回当前遮罩类型。

        Returns:
            transparent / opaque / blur。
        """
        return self._backdrop_kind

    def is_dismissable(self) -> bool:
        """是否允许点遮罩关闭。

        Returns:
            True 表示允许。
        """
        return self._is_dismissable

    def is_keyboard_dismiss_disabled(self) -> bool:
        """是否禁用了 Esc 关闭。

        Returns:
            True 表示已禁用。
        """
        return self._is_keyboard_dismiss_disabled

    def disable_animation(self) -> bool:
        """是否关闭了动画。

        Returns:
            True 表示动画已关闭。
        """
        return self._disable_animation
