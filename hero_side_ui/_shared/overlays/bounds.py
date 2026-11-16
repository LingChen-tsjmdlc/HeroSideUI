"""浮层与宿主窗口：把弹层超出宿主窗口客户区的部分裁掉，并提供窗口内可用空间。"""

from __future__ import annotations

import shiboken6
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication, QRegion
from PySide6.QtWidgets import QWidget

# 沿 _hs_host_window 回溯的最大层数
_MAX_HOST_HOPS = 8


def register_host(popup: QWidget, anchor: QWidget) -> None:
    """记录浮层所属的宿主窗口，浮层里再开的浮层据此找回应用窗口。

    Args:
        popup: 浮层（顶层窗口）。
        anchor: 触发浮层的控件。
    """
    popup._hs_host_window = host_window(anchor)  # type: ignore[attr-defined]


def host_window(widget: QWidget) -> QWidget | None:
    """返回控件所在的应用窗口；控件在浮层里时回溯到浮层的宿主窗口。

    Args:
        widget: 任意控件。
    """
    if widget is None or not shiboken6.isValid(widget):
        return None
    win = widget.window()
    for _ in range(_MAX_HOST_HOPS):
        nxt = getattr(win, "_hs_host_window", None)
        if nxt is None or not shiboken6.isValid(nxt) or nxt is win:
            break
        win = nxt
    return win


def screen_rect(widget: QWidget) -> QRect:
    """控件所在屏幕的可用区域（多屏取控件所在屏）。

    Args:
        widget: 任意控件。
    """
    handle = widget.window().windowHandle()
    screen = handle.screen() if handle is not None else None
    if screen is None:
        screen = QGuiApplication.screenAt(widget.mapToGlobal(QPoint(0, 0)))
    screen = screen or QGuiApplication.primaryScreen()
    return screen.availableGeometry() if screen is not None else QRect(0, 0, 1920, 1080)


def host_rect(widget: QWidget) -> QRect | None:
    """宿主窗口客户区的全局矩形；窗口未显示或已最小化时为 None。

    Args:
        widget: 触发浮层的控件。
    """
    win = host_window(widget)
    if win is None or not win.isVisible() or win.isMinimized():
        return None
    return QRect(win.mapToGlobal(QPoint(0, 0)), win.size())


def popup_area(widget: QWidget) -> QRect:
    """弹层可见主体应当落在的全局矩形：宿主窗口客户区与所在屏幕可用区的交集。

    Args:
        widget: 触发浮层的控件。

    Returns:
        窗口未显示或与屏幕不相交时退回屏幕可用区。
    """
    screen = screen_rect(widget)
    win = host_rect(widget)
    if win is None:
        return screen
    area = win.intersected(screen)
    return area if area.width() > 0 and area.height() > 0 else screen


def overflow(body: QRect, area: QRect) -> int:
    """body 超出 area 的总像素数（四个方向相加，0 表示完全在内）。

    Args:
        body: 弹层可见主体的全局矩形。
        area: 允许区域。
    """
    return (
        max(0, area.left() - body.left())
        + max(0, body.right() - area.right())
        + max(0, area.top() - body.top())
        + max(0, body.bottom() - area.bottom())
    )


def clip_to_host(popup: QWidget, anchor: QWidget | None) -> None:
    """用 mask 去掉 popup 超出宿主窗口客户区的部分（窗口不可用时不裁）。

    Args:
        popup: 浮层（顶层窗口）。
        anchor: 触发浮层的控件。
    """
    rect = host_rect(anchor) if anchor is not None and shiboken6.isValid(anchor) else None
    if rect is None:
        popup.clearMask()
        return
    local = QRect(popup.mapFromGlobal(rect.topLeft()), rect.size()).intersected(popup.rect())
    if local == popup.rect():
        popup.clearMask()
    else:
        popup.setMask(QRegion(local))


def space_below(widget: QWidget) -> int:
    """控件下沿到允许区域底部的可用高度（允许区域 = 宿主窗口 ∩ 所在屏幕可用区）。

    Args:
        widget: 触发浮层的控件。

    Note:
        必须和浮层最终落位用同一个区域（popup_area）：窗口超出屏幕可用区时（如 macOS 菜单栏下），
        只量到窗口边缘会把菜单上限算大，翻转后被夹到屏幕边缘，压在触发器上。
    """
    area = popup_area(widget)
    return area.bottom() - (widget.mapToGlobal(QPoint(0, 0)).y() + widget.height())


def space_above(widget: QWidget) -> int:
    """控件上沿到允许区域顶部的可用高度（允许区域 = 宿主窗口 ∩ 所在屏幕可用区）。

    Args:
        widget: 触发浮层的控件。

    Note:
        同 space_below：与 popup_area 保持同一个区域。
    """
    area = popup_area(widget)
    return widget.mapToGlobal(QPoint(0, 0)).y() - area.top()


__all__ = [
    "clip_to_host",
    "host_rect",
    "host_window",
    "overflow",
    "popup_area",
    "register_host",
    "screen_rect",
    "space_above",
    "space_below",
]
