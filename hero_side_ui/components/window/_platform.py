"""Window 的平台层：最大化 / 全屏 / 拖动、命中测试、Windows 原生消息入口。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication

from ...themes import WINDOW_SPEC
from . import _native
from ._title_bar import is_drag_area

# 缩放热区命中结果：键为 (在左边缘, 在右边缘, 在上边缘, 在下边缘)
_EDGE_HITS = {
    (True, False, True, False): _native.HTTOPLEFT,
    (False, True, True, False): _native.HTTOPRIGHT,
    (True, False, False, True): _native.HTBOTTOMLEFT,
    (False, True, False, True): _native.HTBOTTOMRIGHT,
    (True, False, False, False): _native.HTLEFT,
    (False, True, False, False): _native.HTRIGHT,
    (False, False, True, False): _native.HTTOP,
    (False, False, False, True): _native.HTBOTTOM,
}


class _PlatformMixin:
    """最大化与命中测试。Windows 走原生消息，其余平台走 Qt 的系统移动 / 缩放。

    宿主类需提供 _title_bar / _native / _pending_maximize / _was_maximized 等。
    """

    # ============================================================
    # 最大化 / 全屏
    # ============================================================
    def _hwnd(self) -> int | None:
        """原生窗口句柄；未启用原生层或窗口尚未创建返回 None（不会触发创建）。"""
        if not self._native or self.windowHandle() is None:
            return None
        return int(self.winId())

    def isMaximized(self) -> bool:
        """是否最大化：软最大化（被最大尺寸钳制）为真；Windows 上以系统状态为准。"""
        if self._soft_max:
            return True
        hwnd = self._hwnd()
        if hwnd is not None and _native.is_zoomed(hwnd):
            return True
        return super().isMaximized()

    def _maximize_target(self) -> QRect | None:
        """最大化的目标矩形（逻辑坐标）；None 表示按系统方式真最大化。

        Returns:
            每个方向取 min(工作区尺寸, 最大尺寸)，再在工作区内居中。两个方向的最大尺寸
            都不小于工作区时返回 None（真最大化）；否则返回钳制后的矩形。
        """
        screen = self.screen()
        if screen is None:
            return None
        avail = screen.availableGeometry()
        w = min(avail.width(), self._user_max[0])
        h = min(avail.height(), self._user_max[1])
        if w >= avail.width() and h >= avail.height():
            return None
        w, h = max(w, self.minimumWidth()), max(h, self.minimumHeight())
        return QRect(
            avail.x() + (avail.width() - w) // 2,
            avail.y() + (avail.height() - h) // 2,
            w,
            h,
        )

    def _enter_soft_max(self, target: QRect):
        """软最大化：记下当前几何，把窗口放到目标矩形。

        Args:
            target: _maximize_target 算出的矩形。
        """
        if not self._soft_max:
            self._normal_geometry = self.geometry()
        self._soft_target = target
        self._soft_busy = True
        try:
            self.setGeometry(target)
        finally:
            self._soft_busy = False
        self._soft_max = True
        if not self.isVisible():
            self.show()
        self._on_state_changed()

    def _leave_soft_max(self, restore: bool):
        """退出软最大化。

        Args:
            restore: True 时把窗口放回进入前的几何。
        """
        if not self._soft_max:
            return
        self._soft_max = False
        if restore and self._normal_geometry is not None:
            self._soft_busy = True
            try:
                self.setGeometry(self._normal_geometry)
            finally:
                self._soft_busy = False
        self._on_state_changed()

    def _check_soft_max(self):
        """软最大化期间窗口被拖动或缩放过：不再算最大化。"""
        if self._soft_max and not self._soft_busy and self.geometry() != self._soft_target:
            self._soft_max = False
            self._on_state_changed()

    def showMaximized(self):
        """最大化。Windows 上直接走系统最大化（Qt 自带的只是拉到屏幕大小）。

        Note:
            设了会小于工作区的最大尺寸时，改为软最大化：钳到最大尺寸并在工作区居中。
        """
        target = self._maximize_target()
        if target is not None:
            self._enter_soft_max(target)
            return
        self._leave_soft_max(restore=False)
        if not self._native:
            super().showMaximized()
            return
        hwnd = self._hwnd()
        if hwnd is None or not self.isVisible():
            self._pending_maximize = True
            self.show()
            return
        _native.maximize(hwnd)

    def showNormal(self):
        """还原。软最大化放回原几何；Windows 上从系统最大化还原。"""
        if self._soft_max:
            self._leave_soft_max(restore=True)
            return
        hwnd = self._hwnd()
        if hwnd is not None and _native.is_zoomed(hwnd):
            _native.restore(hwnd)
            return
        super().showNormal()

    def showFullScreen(self):
        """全屏；软最大化先放回原几何。"""
        self._leave_soft_max(restore=True)
        super().showFullScreen()

    def _toggle_maximize(self):
        """最大化 / 还原（全屏时先退出全屏）。"""
        if self.isFullScreen() or self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _toggle_fullscreen(self):
        """进入 / 退出全屏。"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _on_maximize_clicked(self):
        """最大化按钮点击：mac 默认切全屏，按住 Alt 才是最大化 / 还原。"""
        if self.resolved_system() == "mac" and not (
            QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier
        ):
            self._toggle_fullscreen()
        else:
            self._toggle_maximize()

    def _on_title_double_click(self):
        """双击标题栏空白处：允许最大化时切换。"""
        if self._can_maximize():
            self._toggle_maximize()

    def _start_move(self):
        """请求系统开始拖动窗口（全屏时不拖）。"""
        handle = self.windowHandle()
        if handle is not None and not self.isFullScreen():
            handle.startSystemMove()

    def _on_state_changed(self):
        """窗口状态变化：同步按钮图标、圆角、缩放热区，并发出 maximized_changed。"""
        maximized, fullscreen = self.isMaximized(), self.isFullScreen()
        self._title_bar.controls().set_window_state(maximized or fullscreen, fullscreen)
        self._sync_frame()
        self._sync_grips()
        if not fullscreen:
            self._ensure_native_styles()
            if self._beta or self._system_square():
                # 阴影在状态切换落定后可能丢，稍后再开一次
                QTimer.singleShot(150, self, self._ensure_native_styles)
        if maximized != self._was_maximized:
            self._was_maximized = maximized
            self.maximized_changed.emit(maximized)

    def _ensure_native_styles(self):
        """补齐系统窗口样式（重建窗口 / 退出全屏后样式可能丢失）；需要时顺带开阴影。"""
        if self._native and self.windowHandle() is not None:
            _native.ensure_styles(int(self.winId()), shadow=self._beta or self._system_square())
            self._sync_system_frame()

    def _system_square(self) -> bool:
        """系统模式且直角（None / 0）：这种窗口系统不给阴影，要自己开。"""
        return (not self._beta) and (self._radius is None or self._radius == 0)

    def _sync_system_frame(self):
        """系统模式：把圆角偏好与边框色交给系统（Windows 11 有效）。"""
        hwnd = self._hwnd()
        if self._beta or hwnd is None:
            return
        c = self._colors.border
        _native.apply_system_frame(hwnd, not self._system_square(), (c.red(), c.green(), c.blue()))

    def _apply_overhang(self):
        """最大化时系统让窗口矩形每边溢出一圈：把内容往里缩进溢出的量，溢出的一圈保持透明。"""
        hwnd = self._hwnd()
        if hwnd is None:
            overhang = (0, 0, 0, 0)
        else:
            dpr = self.devicePixelRatioF()
            overhang = tuple(round(v / dpr) for v in _native.window_overhang(hwnd))
        if overhang != self._overhang:
            self._overhang = overhang
            self._root_layout.setContentsMargins(*overhang)
            self.update()

    # ============================================================
    # 命中测试（Windows 原生）
    # ============================================================
    def _hit_test(self, pos: QPoint) -> int:
        """窗口内某点的命中结果，返回值就是 Win32 的 HT* 常量。

        Args:
            pos: 窗口坐标系下的点。
        """
        w, h = self.width(), self.height()
        if self._flag("resizable") and not self._is_expanded():
            e = WINDOW_SPEC["resize_edge"]
            key = (pos.x() < e, pos.x() >= w - e, pos.y() < e, pos.y() >= h - e)
            hit = _EDGE_HITS.get(key)
            if hit is not None:
                return hit
        bar = self._title_bar
        if bar.y() <= pos.y() < bar.y() + bar.height():
            if self._can_maximize() and self.resolved_system() != "mac":
                controls = bar.controls()
                rect = controls.button_rect("maximize").translated(controls.pos() + bar.pos())
                if rect.contains(pos):
                    return _native.HTMAXBUTTON
            return _native.HTCAPTION if is_drag_area(self.childAt(pos), bar) else _native.HTCLIENT
        return _native.HTCLIENT

    def native_hit_test(self, x: int, y: int) -> int:
        """（原生层回调）按窗口内偏移命中测试。

        Args:
            x: 相对窗口左上角的横向偏移，设备像素。
            y: 纵向偏移，设备像素。
        """
        dpr = self.devicePixelRatioF()
        return self._hit_test(QPoint(round(x / dpr), round(y / dpr)))

    def native_can_maximize(self) -> bool:
        """（原生层回调）是否放行系统的双击最大化。"""
        return self._can_maximize()

    def native_max_state(self, hover: bool, down: bool):
        """（原生层回调）最大化按钮在非客户区的悬停 / 按下态。"""
        self._title_bar.controls().button("maximize").set_native_state(hover, down)

    def native_max_clicked(self):
        """（原生层回调）最大化按钮被点击或双击标题栏；延后一拍切换，不在消息处理里同步改状态。"""
        QTimer.singleShot(0, self, self._toggle_maximize)

    def nativeEvent(self, event_type, message):
        """Windows：交给原生层处理 NCCALCSIZE / NCHITTEST 等消息。"""
        if self._native:
            result = _native.handle_message(self, event_type, message)
            if result is not None:
                return result
        return super().nativeEvent(event_type, message)


__all__ = ["_PlatformMixin"]
