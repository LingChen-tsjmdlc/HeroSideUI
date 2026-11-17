"""Windows 原生层：补窗口样式、吃掉系统标题栏、原生命中测试。

只在 Windows 平台插件下启用。目的：保留系统的贴边吸附、最小化 / 还原动画，
并让最大化按钮能触发 Windows 11 的 Snap Layouts（悬停弹出分屏布局）。

实验结论（见 docs/window.md）：只返回 HTMAXBUTTON 不够，窗口必须带
WS_CAPTION | WS_THICKFRAME | WS_MAXIMIZEBOX 样式。Qt 的 showMaximized() 在这种窗口上
只是把窗口拉到屏幕大小（IsZoomed 为 False），必须直接调 ShowWindow。
透明窗口是分层窗口，位图按"窗口矩形"而不是客户区贴。系统最大化会让窗口矩形每边多出
约 8px，这一步无法拦截（连跳过 Qt 的处理、事后 SetWindowPos 也一样），所以最大化时由
Window 按 window_overhang() 测得的量把内容往里缩进。
"""

from __future__ import annotations

import ctypes
import functools
import os
import sys
from ctypes import wintypes
from typing import Protocol

from PySide6.QtGui import QGuiApplication

# ---- 窗口消息 ----
WM_GETMINMAXINFO = 0x0024
WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
WM_NCMOUSEMOVE = 0x00A0
WM_NCLBUTTONDOWN = 0x00A1
WM_NCLBUTTONUP = 0x00A2
WM_NCLBUTTONDBLCLK = 0x00A3
WM_NCMOUSELEAVE = 0x02A2

# ---- 命中测试结果 ----
HTCLIENT = 1
HTCAPTION = 2
HTMAXBUTTON = 9
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

# ---- 窗口样式 ----
_GWL_STYLE = -16
_WS_CAPTION = 0x00C00000
_WS_THICKFRAME = 0x00040000
_WS_MINIMIZEBOX = 0x00020000
_WS_MAXIMIZEBOX = 0x00010000
_REQUIRED_STYLES = _WS_CAPTION | _WS_THICKFRAME | _WS_MINIMIZEBOX | _WS_MAXIMIZEBOX

_SWP_FRAMECHANGED = 0x0020
_SWP_NOMOVE = 0x0002
_SWP_NOSIZE = 0x0001
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_REFRESH = _SWP_FRAMECHANGED | _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_NOACTIVATE

_SW_MAXIMIZE = 3
_SW_RESTORE = 9

_MONITOR_DEFAULTTONEAREST = 2
# 无上限时 ptMaxTrackSize 的取值（系统允许的最大窗口边长量级）
_TRACK_LIMIT = 16384
# WM_NCCALCSIZE 的返回值：WVR_HREDRAW | WVR_VREDRAW，整个客户区重画且丢弃旧像素
_WVR_REDRAW = 0x0300
# 真最大化时系统在工作区之外多加的边框（约每边 8px，随 DPI 变），留足余量
_FRAME_SLACK = 64

_TME_LEAVE = 0x00000002
_TME_NONCLIENT = 0x00000010


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MINMAXINFO(ctypes.Structure):
    _fields_ = [
        ("ptReserved", _POINT),
        ("ptMaxSize", _POINT),
        ("ptMaxPosition", _POINT),
        ("ptMinTrackSize", _POINT),
        ("ptMaxTrackSize", _POINT),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class _TRACKMOUSEEVENT(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("hwndTrack", wintypes.HWND),
        ("dwHoverTime", wintypes.DWORD),
    ]


_user32 = None
_get_style = None
_set_style = None
if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32")
    _get_style = getattr(_user32, "GetWindowLongPtrW", None) or _user32.GetWindowLongW
    _set_style = getattr(_user32, "SetWindowLongPtrW", None) or _user32.SetWindowLongW
    _get_style.restype = ctypes.c_ssize_t
    _get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    _set_style.restype = ctypes.c_ssize_t
    _set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    _user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    _user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.IsZoomed.argtypes = [wintypes.HWND]
    _user32.TrackMouseEvent.argtypes = [ctypes.POINTER(_TRACKMOUSEEVENT)]
    _user32.MonitorFromWindow.restype = wintypes.HANDLE
    _user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    _user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_MONITORINFO)]
    _user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_RECT)]


class NativeHost(Protocol):
    """原生层需要窗口实现的回调。"""

    def native_hit_test(self, x: int, y: int) -> int:
        """按窗口内偏移（设备像素）返回 HT* 命中结果。"""

    def native_can_maximize(self) -> bool:
        """当前是否允许最大化（决定是否放行系统的双击最大化）。"""

    def native_max_state(self, hover: bool, down: bool) -> None:
        """最大化按钮的悬停 / 按下态（非客户区没有 Qt 鼠标事件，由消息驱动）。"""

    def native_max_clicked(self) -> None:
        """最大化按钮被点击，切换最大化 / 还原。"""

    def native_size_limits(self) -> tuple[int, int, int, int]:
        """窗口最小 / 最大尺寸，设备像素：(最小宽, 最小高, 最大宽, 最大高)。"""


def available() -> bool:
    """是否应启用原生层：Windows 且平台插件是 windows（offscreen 等不启用）。"""
    return sys.platform == "win32" and QGuiApplication.platformName() == "windows"


@functools.lru_cache(maxsize=1)
def _d3d11_usable() -> bool:
    """本机能否创建 D3D11 硬件设备（探测一次）。

    Note:
        Qt 在 D3D11 创建失败时只打一行日志，窗口会黑屏（实测），所以设 RHI 变量前先自己试一次。
    """
    try:
        d3d11 = ctypes.WinDLL("d3d11")
        device = ctypes.c_void_p()
        # D3D_DRIVER_TYPE_HARDWARE = 1，D3D11_SDK_VERSION = 7
        hr = d3d11.D3D11CreateDevice(
            None, 1, None, 0, None, 0, 7, ctypes.byref(device), None, None
        )
        if hr >= 0 and device.value:
            # 立刻释放：IUnknown::Release 是虚表第 3 项
            vtbl = ctypes.cast(device, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
            release(device)
            return True
    except (OSError, AttributeError):
        pass
    return False


def prefer_rhi() -> bool:
    """让 Qt 用 D3D11 合成窗口，避免透明窗口走"分层窗口"路径；只给自绘圆角（beta）窗口用。

    Returns:
        True 表示 D3D11 已启用（或使用者自己设过）；False 表示没启用，窗口走默认路径（缩放可能闪）。

    Note:
        透明窗口默认走分层窗口（UpdateLayeredWindow）：缩放时系统要等整张位图提交完才更新，
        帧率低且会漏画，表现为缩放闪烁（实测系统改尺寸次数只有不透明窗口的 1/7，约 4 成步骤漏画）。
        QT_WIDGETS_RHI 让 Qt 改用 D3D11 提交，实测不再闪。
        - 这是进程级设置：之后创建的所有顶层窗口都走 D3D11。
        - Qt 只在第一个顶层窗口显示时读一次，之后再设无效，所以要在应用里最早的窗口之前创建自绘圆角窗口。
        - 使用者自己设过 QT_WIDGETS_RHI 就不碰；HSUI_WINDOW_RHI=0 可关闭；探测失败不设（避免黑屏）。
    """
    if not available() or os.environ.get("HSUI_WINDOW_RHI") == "0":
        return False
    if "QT_WIDGETS_RHI" in os.environ:
        return True
    if not _d3d11_usable():
        return False
    os.environ["QT_WIDGETS_RHI"] = "1"
    os.environ.setdefault("QT_WIDGETS_RHI_BACKEND", "d3d11")
    return True


class _MARGINS(ctypes.Structure):
    _fields_ = [("left", ctypes.c_int), ("right", ctypes.c_int), ("top", ctypes.c_int), ("bottom", ctypes.c_int)]


def apply_system_frame(hwnd: int, rounded: bool, border_rgb: tuple[int, int, int]) -> None:
    """系统模式：设置系统圆角偏好与边框颜色（Windows 11 有效，更早的系统静默忽略）。

    Args:
        hwnd: 窗口句柄。
        rounded: True 用系统圆角，False 直角。
        border_rgb: 边框颜色 (r, g, b)。
    """
    try:
        dwm = ctypes.WinDLL("dwmapi")
        corner = ctypes.c_int(2 if rounded else 1)  # DWMWCP_ROUND / DWMWCP_DONOTROUND
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner), 4)
        r, g, b = border_rgb
        colorref = ctypes.c_uint(r | (g << 8) | (b << 16))  # COLORREF = 0x00BBGGRR
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(colorref), 4)
    except OSError:
        pass


def enable_shadow(hwnd: int) -> None:
    """开启系统阴影：DWM 非客户区渲染关再开，并把边框向客户区扩展 1px。

    Note:
        透明窗口默认没有系统阴影（实测窗口外 0 个变暗像素）。开启后 DWM 会在窗口外画柔和阴影，
        最大化时系统自动不画。最大化 / 还原、最小化 / 还原、隐藏再显示之后阴影会丢，而重复设同
        一个值不起作用，必须先关再开，所以每次状态变化后都要重新调一遍。失败不影响窗口使用。
    """
    try:
        dwm = ctypes.WinDLL("dwmapi")
        for value in (1, 2):  # DWMNCRP_DISABLED -> DWMNCRP_ENABLED
            policy = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(policy), 4)
        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(_MARGINS(1, 1, 1, 1)))
    except OSError:
        pass


def ensure_styles(hwnd: int, shadow: bool = False) -> bool:
    """补齐 WS_CAPTION / THICKFRAME / MIN / MAXIMIZEBOX；自绘圆角的窗口再开启系统阴影。

    Args:
        hwnd: 窗口句柄。
        shadow: 是否开启系统阴影（透明窗口默认没有阴影，系统模式的不透明窗口自带）。

    Returns:
        True 表示本次确实改了样式。已齐全时不改样式（阴影每次都会重做）。
    """
    style = _get_style(hwnd, _GWL_STYLE)
    changed = style & _REQUIRED_STYLES != _REQUIRED_STYLES
    if changed:
        _set_style(hwnd, _GWL_STYLE, style | _REQUIRED_STYLES)
        _user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, _SWP_REFRESH)
    if shadow:
        enable_shadow(hwnd)
    return changed


def is_zoomed(hwnd: int) -> bool:
    """系统层面是否最大化（Qt 的 isMaximized 在假最大化时也为真，不可用）。

    Args:
        hwnd: 窗口句柄。
    """
    return bool(_user32.IsZoomed(hwnd))


def maximize(hwnd: int) -> None:
    """真最大化。"""
    _user32.ShowWindow(hwnd, _SW_MAXIMIZE)


def restore(hwnd: int) -> None:
    """从最大化 / 最小化还原。"""
    _user32.ShowWindow(hwnd, _SW_RESTORE)


def _work_area(hwnd: int) -> _RECT | None:
    """窗口所在显示器的工作区（不含任务栏）；取不到返回 None。"""
    monitor = _user32.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
    mi = _MONITORINFO()
    mi.cbSize = ctypes.sizeof(_MONITORINFO)
    if monitor and _user32.GetMonitorInfoW(monitor, ctypes.byref(mi)):
        return mi.rcWork
    return None


def window_overhang(hwnd: int) -> tuple[int, int, int, int]:
    """最大化时窗口矩形超出工作区的量（左, 上, 右, 下），设备像素；未最大化为全 0。

    Args:
        hwnd: 窗口句柄。

    Note:
        系统最大化会让窗口矩形每边多出一圈边框厚度（约 8px），无法拦截，连 Qt 的处理也
        跳过、事后 SetWindowPos 也一样（系统每次都会再加回去）。分层窗口的位图按窗口矩形
        贴，所以由 Window 按这里测得的量把内容往里缩进，溢出的一圈保持透明。
    """
    if not is_zoomed(hwnd):
        return 0, 0, 0, 0
    work = _work_area(hwnd)
    if work is None:
        return 0, 0, 0, 0
    cur = _RECT()
    _user32.GetWindowRect(hwnd, ctypes.byref(cur))
    return (
        max(0, work.left - cur.left),
        max(0, work.top - cur.top),
        max(0, cur.right - work.right),
        max(0, cur.bottom - work.bottom),
    )


def _fill_minmaxinfo(host: NativeHost, hwnd: int, lparam: int) -> None:
    """填写 WM_GETMINMAXINFO：最大化范围、最小 / 最大尺寸。

    Args:
        host: 窗口。
        hwnd: 窗口句柄。
        lparam: MINMAXINFO 指针。

    Note:
        最大化范围 = 工作区与最大尺寸逐方向取小，并在工作区居中，所以系统发起的最大化
        （如拖到屏幕顶端）也遵守钳制。最大尺寸不小于工作区的方向，跟踪上限要留出系统
        最大化时多出的边框，否则真最大化会被最大尺寸卡住。
    """
    info = _MINMAXINFO.from_address(lparam)
    min_w, min_h, max_w, max_h = host.native_size_limits()
    work = _work_area(hwnd)
    track_w, track_h = min(max_w, _TRACK_LIMIT), min(max_h, _TRACK_LIMIT)
    if work is not None:
        monitor = _user32.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
        mi = _MONITORINFO()
        mi.cbSize = ctypes.sizeof(_MONITORINFO)
        _user32.GetMonitorInfoW(monitor, ctypes.byref(mi))
        work_w, work_h = work.right - work.left, work.bottom - work.top
        size_w, size_h = min(work_w, max_w), min(work_h, max_h)
        info.ptMaxSize.x = size_w
        info.ptMaxSize.y = size_h
        info.ptMaxPosition.x = work.left - mi.rcMonitor.left + (work_w - size_w) // 2
        info.ptMaxPosition.y = work.top - mi.rcMonitor.top + (work_h - size_h) // 2
        if max_w >= work_w:
            track_w = max(track_w, work_w + _FRAME_SLACK)
        if max_h >= work_h:
            track_h = max(track_h, work_h + _FRAME_SLACK)
    info.ptMinTrackSize.x = min_w
    info.ptMinTrackSize.y = min_h
    info.ptMaxTrackSize.x = track_w
    info.ptMaxTrackSize.y = track_h


def _track_leave(hwnd: int) -> None:
    """请求在鼠标离开非客户区时收到 WM_NCMOUSELEAVE。"""
    tme = _TRACKMOUSEEVENT(ctypes.sizeof(_TRACKMOUSEEVENT), _TME_LEAVE | _TME_NONCLIENT, hwnd, 0)
    _user32.TrackMouseEvent(ctypes.byref(tme))


def handle_message(host: NativeHost, event_type, message) -> tuple[bool, int] | None:
    """处理一条窗口消息。

    Args:
        host: 窗口。
        event_type: Qt nativeEvent 的类型参数。
        message: Qt nativeEvent 的消息指针（MSG*）。

    Returns:
        (True, 结果) 表示已处理；None 表示交给 Qt 默认处理。

    Note:
        消息处理期间禁止访问 winId()：窗口创建期重入会让 CreateWindowEx 失败，
        句柄一律取自 msg.hWnd。
    """
    if bytes(event_type) != b"windows_generic_MSG":
        return None
    msg = wintypes.MSG.from_address(int(message))
    code = msg.message

    if code == WM_NCCALCSIZE:
        # 客户区 = 整个窗口，等于吃掉系统标题栏与边框。
        # 缩放时返回 WVR_REDRAW：告诉系统整个客户区都要重画，不要把旧像素搬到新位置
        # （默认的搬运与 Qt 的重绘错开一帧，会出现内容整体平移、被裁掉的闪烁帧）。
        return True, (_WVR_REDRAW if msg.wParam else 0)

    if code == WM_GETMINMAXINFO:
        _fill_minmaxinfo(host, msg.hWnd, msg.lParam)
        return True, 0

    if code == WM_NCHITTEST:
        # lParam 是屏幕物理像素坐标：换成相对窗口左上角的偏移再交给窗口，不依赖 QCursor
        rect = _RECT()
        _user32.GetWindowRect(msg.hWnd, ctypes.byref(rect))
        gx = ctypes.c_short(msg.lParam & 0xFFFF).value
        gy = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
        return True, host.native_hit_test(gx - rect.left, gy - rect.top)

    if code == WM_NCMOUSEMOVE:
        if msg.wParam == HTMAXBUTTON:
            host.native_max_state(True, False)
            _track_leave(msg.hWnd)
        else:
            host.native_max_state(False, False)
        return None

    if code == WM_NCMOUSELEAVE:
        host.native_max_state(False, False)
        return None

    if code == WM_NCLBUTTONDOWN and msg.wParam == HTMAXBUTTON:
        host.native_max_state(True, True)
        return True, 0

    if code == WM_NCLBUTTONUP and msg.wParam == HTMAXBUTTON:
        host.native_max_state(True, False)
        host.native_max_clicked()
        return True, 0

    if code == WM_NCLBUTTONDBLCLK and msg.wParam in (HTCAPTION, HTMAXBUTTON):
        # 不交给系统：系统会直接最大化，绕过窗口对最大尺寸的钳制；统一由窗口自己切换
        if msg.wParam == HTCAPTION and host.native_can_maximize():
            host.native_max_clicked()
        return True, 0
    return None


__all__ = [
    "HTBOTTOM",
    "HTBOTTOMLEFT",
    "HTBOTTOMRIGHT",
    "HTCAPTION",
    "HTCLIENT",
    "HTLEFT",
    "HTMAXBUTTON",
    "HTRIGHT",
    "HTTOP",
    "HTTOPLEFT",
    "HTTOPRIGHT",
    "NativeHost",
    "apply_system_frame",
    "available",
    "enable_shadow",
    "prefer_rhi",
    "ensure_styles",
    "handle_message",
    "is_zoomed",
    "maximize",
    "restore",
    "window_overhang",
]
