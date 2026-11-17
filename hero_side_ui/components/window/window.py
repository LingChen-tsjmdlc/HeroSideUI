"""Window 无边框窗口：自绘标题栏（左 / 中 / 右三个槽 + 窗口控制按钮）。

桌面端专属组件（HeroUI v2 无对应项），API 见 docs/window.md。
主窗口、子窗口、模态窗口都用它；配置默认继承最近的 Window 祖先。
配置继承在 _config、尺寸限制在 _sizing、最大化与命中测试在 _platform。
"""

from __future__ import annotations

import weakref

from PySide6.QtCore import QEvent, QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ...core import ThemeProvider
from ...themes import (
    VALID_WINDOW_SYSTEMS,
    WINDOW_SPEC,
)
from ...utils import clear_layout, safe_delete
from . import _native
from ._config import (
    QWIDGETSIZE_MAX,
    _ConfigMixin,
    check_bool,
    check_choice,
    check_int,
    check_radius,
    is_custom_radius,
    radius_to_px,
)
from ._frame import _FrameOverlay, _GripSet, rounded_path
from ._platform import _PlatformMixin
from ._sizing import _SizeMixin
from ._style import window_colors
from ._title_bar import _TitleBar, _TitleWidget

_VALID_THEMES = ("auto", "light", "dark")
_SLOT_NAMES = ("left", "center", "right")


class Window(_ConfigMixin, _SizeMixin, _PlatformMixin, QWidget):
    """无边框窗口。API/示例见 ``docs/window.md``。"""

    # 最大化状态变化（含系统层面的最大化）
    maximized_changed = Signal(bool)
    # 解析后的风格变化（windows / mac / linux）
    system_changed = Signal(str)

    _ready = False
    _native = False
    _beta = False
    _overhang = (0, 0, 0, 0)
    # 软最大化：被最大尺寸钳制的"最大化"，只是把窗口放到目标矩形，不走系统最大化
    _soft_max = False
    _soft_busy = False
    _soft_target = None
    _normal_geometry = None

    def __init__(
        self,
        *,
        system: str | None = None,
        radius: str | float | None = "system",
        title_bar_height: int | None = None,
        show_minimize: bool | None = None,
        show_maximize: bool | None = None,
        show_close: bool | None = None,
        resizable: bool | None = None,
        width: int = WINDOW_SPEC["default_width"],
        height: int = WINDOW_SPEC["default_height"],
        min_width: int | None = None,
        min_height: int | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
        theme: str = "auto",
        parent: QWidget | None = None,
    ):
        """创建窗口。

        Args:
            system: auto / windows / mac / linux；None 跟随父窗口，无父窗口为 auto。
            radius: 圆角，构造时决定模式，不继承父窗口。
                "system"（默认）：不透明窗口，圆角与阴影由系统决定（Windows 11 有圆角，Windows 10 直角）；
                None 或 0：直角；
                "sm" / "md" / "lg" 或大于 0 的数字（像素）：自绘超椭圆圆角，全平台一致（beta，
                    透明窗口，Windows 上自动启用 D3D11 避免缩放闪烁）。
            title_bar_height: 标题栏高度 px（最小 20）；None 跟随父窗口，无父窗口按风格取标准值。
            show_minimize: 显示最小化按钮；None 跟随父窗口，无父窗口为 True。
            show_maximize: 显示最大化 / 还原按钮（mac 为缩放按钮）；None 同上。
            show_close: 显示关闭按钮；None 同上。
            resizable: 能否拖边缘缩放，False 时同时隐藏最大化；None 同上。
            width: 初始宽度，不继承。
            height: 初始高度，不继承。
            min_width: 最小宽度；None 取保底值，不继承。
            min_height: 最小高度；None 取保底值，不继承。
            max_width: 最大宽度；None 不限，不继承。
            max_height: 最大高度；None 不限，不继承。
            theme: auto / light / dark。
            parent: 传了就是子窗口：在父窗口之上，不单独占任务栏。

        Raises:
            ValueError: 任一参数取值非法。
        """
        check_choice("system", system, VALID_WINDOW_SYSTEMS)
        check_radius(radius)
        check_int("title_bar_height", title_bar_height)
        for name, v in (
            ("show_minimize", show_minimize),
            ("show_maximize", show_maximize),
            ("show_close", show_close),
            ("resizable", resizable),
        ):
            check_bool(name, v)
        check_int("width", width)
        check_int("height", height)
        for name, v in (
            ("min_width", min_width),
            ("min_height", min_height),
            ("max_width", max_width),
            ("max_height", max_height),
        ):
            check_int(name, v, minimum=0)
        if theme not in _VALID_THEMES:
            raise ValueError(f"theme must be one of {_VALID_THEMES}, got {theme!r}")

        # 模式在构造时定：自绘圆角（beta）= 透明窗口 + D3D11 + 自绘超椭圆；否则 = 不透明窗口 + 系统圆角
        self._beta = is_custom_radius(radius)
        self._radius = radius
        if self._beta:
            _native.prefer_rhi()  # 必须在第一个窗口显示之前：透明窗口缩放闪烁的缓解，见 prefer_rhi
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        if self._beta:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._native = _native.available()

        self._own: dict[str, object] = {
            "system": system,
            "title_bar_height": None if title_bar_height is None else int(title_bar_height),
            "show_minimize": show_minimize,
            "show_maximize": show_maximize,
            "show_close": show_close,
            "resizable": resizable,
        }
        self._user_min = (int(min_width or 0), int(min_height or 0))
        self._user_max = (
            int(max_width) if max_width else QWIDGETSIZE_MAX,
            int(max_height) if max_height else QWIDGETSIZE_MAX,
        )
        QWidget.setMaximumSize(self, *self._user_max)
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._colors = window_colors(self._theme)
        self._applied: tuple | None = None
        self._was_maximized = False
        self._pending_maximize = False
        self._user_slots: dict[str, QWidget | None] = dict.fromkeys(_SLOT_NAMES)
        self._title_widgets: weakref.WeakSet = weakref.WeakSet()

        # ---- 子件 ----
        self._title_bar = _TitleBar(self)
        self._content_host = QWidget(self)
        self._content_layout = QVBoxLayout(self._content_host)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._title_bar)
        root.addWidget(self._content_host, 1)
        self._root_layout = root
        self._overhang = (0, 0, 0, 0)
        self._overlay = _FrameOverlay(self)
        self._grips = _GripSet(self)

        self._default_title = self._make_title_widget()
        self._title_bar.drag_requested.connect(self._start_move)
        self._title_bar.double_clicked.connect(self._on_title_double_click)
        controls = self._title_bar.controls()
        controls.button("minimize").clicked.connect(lambda *_: self.showMinimized())
        controls.button("maximize").clicked.connect(lambda *_: self._on_maximize_clicked())
        controls.button("close").clicked.connect(lambda *_: self.close())

        self._ready = True
        self._apply_all()
        self.resize(
            max(self.minimumWidth(), min(int(width), self.maximumWidth())),
            max(self.minimumHeight(), min(int(height), self.maximumHeight())),
        )

        if theme == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # 应用配置
    # ============================================================
    def _child_windows(self) -> list[Window]:
        """所有后代 Window（子窗口及其子窗口）。"""
        return self.findChildren(Window)

    def _apply_all(self):
        """按解析后的配置刷新标题栏、最小尺寸、外框与缩放热区；没有变化则什么都不做。"""
        if not self._ready:
            return
        system = self.resolved_system()
        tbh = self.resolved_title_bar_height()
        visible = self._visible_buttons()
        snap = (
            system,
            self._radius,
            tbh,
            tuple(visible.values()),
            self._flag("resizable"),
            self._theme,
        )
        if snap == self._applied:
            return
        old_system = self._applied[0] if self._applied else None
        self._applied = snap

        self._title_bar.configure(system, self._theme, tbh, visible)
        for tw in list(self._title_widgets):
            tw.set_system(system)
        self._place_titles(system)
        self._apply_min_size()
        self._sync_frame()
        self._sync_grips()
        if old_system is not None and old_system != system:
            self.system_changed.emit(system)

    def _is_expanded(self) -> bool:
        """真最大化或全屏：圆角归零、不描边、关闭缩放。软最大化窗口没占满屏幕，不算。"""
        return (self.isMaximized() and not self._soft_max) or self.isFullScreen()

    def _radius_px(self) -> float:
        """当前要自绘的圆角像素；系统模式由系统画，这里恒为 0。"""
        if not self._beta or self._is_expanded():
            return 0.0
        return radius_to_px(self._radius)

    def _sync_frame(self):
        """同步溢出缩进、圆角与描边到覆盖层（自绘模式）或系统（系统模式）并重绘。"""
        self._apply_overhang()
        if self._beta:
            self._overlay.apply(self._radius_px(), self._colors.border, not self._is_expanded())
            self._overlay.raise_()
        else:
            self._overlay.hide()
            self._sync_system_frame()
        self.update()

    def _sync_grips(self):
        """非原生平台：按可缩放与否启停 8 个缩放热区。"""
        active = (not self._native) and self._flag("resizable") and not self._is_expanded()
        self._grips.set_active(active)
        self._grips.relayout(self.width(), self.height(), WINDOW_SPEC["resize_edge"])

    # ============================================================
    # 内容与槽
    # ============================================================
    def set_content(self, widget: QWidget | None):
        """设置内容区，旧内容由窗口销毁。

        Args:
            widget: 新内容；None 只清空。
        """
        clear_layout(self._content_layout)
        if widget is not None:
            widget.setParent(self._content_host)
            self._content_layout.addWidget(widget)
            widget.show()
        self._overlay.raise_()

    def content_widget(self) -> QWidget:
        """内容区容器（已带 QVBoxLayout，无边距）。"""
        return self._content_host

    def set_left(self, widget: QWidget | None):
        """替换左槽，旧控件由窗口销毁。

        Args:
            widget: 新控件；None 恢复默认。
        """
        self._set_slot("left", widget)

    def set_center(self, widget: QWidget | None):
        """替换中槽，旧控件由窗口销毁。

        Args:
            widget: 新控件；None 恢复默认。
        """
        self._set_slot("center", widget)

    def set_right(self, widget: QWidget | None):
        """替换右槽，旧控件由窗口销毁。

        Args:
            widget: 新控件；None 恢复默认。
        """
        self._set_slot("right", widget)

    def _set_slot(self, name: str, widget: QWidget | None):
        """放入或清空某个槽；默认的"图标+标题"在没有自定义内容的默认槽里补位。"""
        old = self._user_slots[name]
        if old is widget:
            return
        for other, w in self._user_slots.items():
            if w is widget and widget is not None:
                self._user_slots[other] = None
        self._user_slots[name] = widget
        self._place_titles(self.resolved_system())
        if old is not None and old not in self._user_slots.values():
            safe_delete(old)
        self._title_bar.refresh_layout()

    def _place_titles(self, system: str):
        """按风格把默认标题放进默认槽（windows / linux 在左，mac 在中），其余槽放自定义控件。"""
        target = "center" if system == "mac" else "left"
        for name in _SLOT_NAMES:
            desired = self._user_slots[name]
            if desired is None and name == target:
                desired = self._default_title
            slot = self._title_bar.slot(name)
            if slot.content() is not desired:
                slot.set_content(desired)
        self._title_bar.refresh_layout()

    def _make_title_widget(self) -> _TitleWidget:
        """创建一个跟随窗口标题与图标的"图标+标题"小部件。"""
        tw = _TitleWidget(
            self.windowTitle(),
            self.windowIcon(),
            self.resolved_system(),
            self._theme_mode,
        )
        self.windowTitleChanged.connect(tw.set_title)
        self.windowIconChanged.connect(tw.set_icon)
        self._title_widgets.add(tw)
        return tw

    def default_title_widget(self) -> QWidget:
        """取一个新的"图标+标题"小部件，想保留标题时放进别的槽。

        Returns:
            跟随窗口标题与图标变化的小部件；放进槽之前由调用方持有。
        """
        return self._make_title_widget()

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        """设置主题。

        Args:
            theme: auto 跟随全局，或固定 light / dark。

        Raises:
            ValueError: 取值非法。
        """
        if theme not in _VALID_THEMES:
            raise ValueError(f"theme must be one of {_VALID_THEMES}, got {theme!r}")
        if theme == "auto":
            self._theme_mode = "auto"
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
        self._theme = self._resolve_theme(theme)
        self._refresh_theme()

    def _apply_provider_theme(self, theme: str):
        """接收 ThemeProvider 的主题广播（不重复注册）。"""
        self._theme = theme
        self._refresh_theme()

    def _refresh_theme(self):
        """主题变化后刷新配色。"""
        self._colors = window_colors(self._theme)
        for tw in list(self._title_widgets):
            tw.set_theme(self._theme_mode)
        self._applied = None
        self._apply_all()
        self._title_bar.update()
        self.update()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """auto 取 ThemeProvider 当前主题，其余原样。"""
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # Qt 事件
    # ============================================================
    def paintEvent(self, _event):
        """画窗口底色。自绘模式画圆角底色，描边与圆角外的擦除由覆盖层完成，最大化溢出的一圈不画；
        系统模式整窗铺底色，圆角由系统裁。"""
        if not self._beta:
            QPainter(self).fillRect(self.rect(), self._colors.background)
            return
        left, top, right, bottom = self._overhang
        body = QRectF(self.rect().adjusted(left, top, -right, -bottom))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillPath(rounded_path(body, self._radius_px()), self._colors.background)

    def resizeEvent(self, event):
        """覆盖层跟随窗口，缩放热区重排。"""
        super().resizeEvent(event)
        self._apply_overhang()
        self._overlay.setGeometry(self.rect())
        if self._beta:
            self._overlay.raise_()
        self._sync_grips()
        self._check_soft_max()

    def moveEvent(self, event):
        """软最大化期间被拖走就不再算最大化。"""
        super().moveEvent(event)
        self._check_soft_max()

    def showEvent(self, event):
        """首次显示：补系统样式、处理待执行的最大化，并重新解析继承配置。"""
        super().showEvent(event)
        self._ensure_native_styles()
        self._apply_all()
        self._on_state_changed()
        if self._pending_maximize:
            self._pending_maximize = False
            hwnd = self._hwnd()
            if hwnd is not None:
                _native.maximize(hwnd)

    def changeEvent(self, event):
        """窗口状态 / 激活状态变化时同步外观。"""
        super().changeEvent(event)
        if not self._ready:
            return
        kind = event.type()
        if kind == QEvent.Type.WindowStateChange:
            self._on_state_changed()
        elif kind == QEvent.Type.ActivationChange:
            self._title_bar.controls().set_window_active(self.isActiveWindow())

    def closeEvent(self, event):
        """先关掉仍显示的子窗口，再关自己。"""
        for child in self._child_windows():
            if child.isVisible():
                child.close()
        super().closeEvent(event)


__all__ = ["Window"]
