"""ToastProvider 与全局快捷函数：每窗口懒建 provider，窗口销毁自动回收。"""

from __future__ import annotations

import weakref

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QWidget

from ...themes import TOAST_SPEC, VALID_TOAST_PLACEMENTS
from ._region import ToastRegion
from .toast import Toast

_DEFAULTS = {
    "placement": "bottom-right",
    "max_visible_toasts": TOAST_SPEC["max_visible_toasts"],
    "toast_offset": 0,
    "disable_animation": False,
}

# 每个宿主窗口一个 provider，随窗口销毁自动回收
_providers: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
# key → 拥有它的 provider（close_toast 需要按 key 反查）
_key_owners: dict = {}


class ToastProvider(QObject):
    """把 Toast 堆叠区挂到某个顶层窗口上，并提供 add / close / clear。"""

    def __init__(
        self,
        window: QWidget,
        placement: str = _DEFAULTS["placement"],
        max_visible_toasts: int = _DEFAULTS["max_visible_toasts"],
        toast_offset: int = 0,
        disable_animation: bool = False,
        toast_props: dict | None = None,
    ):
        """初始化 provider 并在宿主窗口上建立 Toast 堆叠区。

        Args:
            window: 承载堆叠区的顶层窗口，同时作为 Qt 父对象。
            placement: toast 的初始弹出位置。
            max_visible_toasts: 同时可见的 toast 数量上限。
            toast_offset: 堆叠区相对窗口边缘的偏移量。
            disable_animation: 为 True 时关闭入场/退场动画。
            toast_props: 追加到每条 toast 的默认属性字典。

        Note:
            懒创建时宿主窗口通常已显示，子 widget 不会自动可见，故显式调用 show 与 raise_。
        """
        super().__init__(window)
        self._window = window
        self._toast_props = dict(toast_props or {})
        self._region = ToastRegion(
            parent=window,
            placement=placement,
            max_visible_toasts=max_visible_toasts,
            toast_offset=toast_offset,
            disable_animation=disable_animation,
        )
        # provider 懒创建时宿主多半已显示，子 widget 不会自动可见，必须显式 show
        self._region.show()
        self._region.raise_()

    # ---- 属性 ----

    @property
    def region(self) -> ToastRegion:
        """返回该 provider 持有的 ToastRegion 堆叠区。"""
        return self._region

    @property
    def placement(self) -> str:
        """返回当前 toast 的弹出位置。"""
        return self._region.placement

    def set_placement(self, placement: str):
        """设置 toast 的弹出位置。"""
        self._region.set_placement(placement)

    def set_max_visible_toasts(self, count: int):
        """设置同时可见的 toast 数量上限。"""
        self._region.set_max_visible_toasts(count)

    def set_toast_offset(self, offset: int):
        """设置堆叠区相对窗口边缘的偏移量。"""
        self._region.set_toast_offset(offset)

    # ---- 队列 ----

    def add(self, **props) -> str:
        """创建一条 toast 并入队，返回它的 key。"""
        merged = dict(self._toast_props)
        merged.update(props)
        placement = merged.pop("placement", None) or self._region.placement
        if isinstance(placement, str) and placement in VALID_TOAST_PLACEMENTS:
            self._region.set_placement(placement)
        card = Toast(placement=placement, parent=self._region, **merged)
        key = self._region.add(card)
        _key_owners[key] = self
        return key

    def card(self, key: str):
        """按 key 取卡片（可继续 set_title / set_loading）。"""
        return self._region.card(key)

    def close(self, key: str):
        """关闭指定 key 的 toast 并移除其归属映射。"""
        self._region.dismiss(key)
        _key_owners.pop(key, None)

    def clear(self):
        """清空该 provider 下的全部 toast 及其归属映射。"""
        for key in list(self._region.keys()):
            _key_owners.pop(key, None)
        self._region.clear()


# ============================================================
# 全局快捷函数
# ============================================================


def configure_toasts(
    placement: str | None = None,
    max_visible_toasts: int | None = None,
    toast_offset: int | None = None,
    disable_animation: bool | None = None,
):
    """修改后续新建 provider 的默认配置（不影响已存在的 provider）。"""
    if placement is not None:
        _DEFAULTS["placement"] = placement
    if max_visible_toasts is not None:
        _DEFAULTS["max_visible_toasts"] = max(1, int(max_visible_toasts))
    if toast_offset is not None:
        _DEFAULTS["toast_offset"] = int(toast_offset)
    if disable_animation is not None:
        _DEFAULTS["disable_animation"] = bool(disable_animation)


def _resolve_window(window: QWidget | None = None) -> QWidget | None:
    """解析宿主窗口：显式指定优先，否则回退到应用的活动窗口。

    Args:
        window: 显式指定的窗口；None 时自动探测。

    Returns:
        解析到的窗口；无 QApplication 或无可用顶层窗口时返回 None。
    """
    if window is not None:
        return window
    app = QApplication.instance()
    if app is None:
        return None
    active = app.activeWindow()
    if active is not None:
        return active
    for widget in app.topLevelWidgets():
        if widget.isWindow() and widget.isVisible():
            return widget
    return None


def get_toast_provider(window: QWidget | None = None) -> ToastProvider:
    """取（必要时创建）指定窗口的 ToastProvider。"""
    host = _resolve_window(window)
    if host is None:
        raise RuntimeError("Toast 需要一个宿主窗口：请先创建 QApplication 与窗口")
    key_host = host.window()
    provider = _providers.get(key_host)
    if provider is None:
        provider = ToastProvider(
            key_host,
            placement=_DEFAULTS["placement"],
            max_visible_toasts=_DEFAULTS["max_visible_toasts"],
            toast_offset=_DEFAULTS["toast_offset"],
            disable_animation=_DEFAULTS["disable_animation"],
        )
        _providers[key_host] = provider
    return provider


def add_toast(
    title: str = "",
    description: str = "",
    *,
    color: str = "default",
    variant: str = "flat",
    radius: str = "md",
    shadow: str = "sm",
    severity: str | None = None,
    icon: str | None = None,
    hide_icon: bool = False,
    hide_close_button: bool = False,
    end_content: QWidget | None = None,
    timeout: int | None = None,
    should_show_timeout_progress: bool = False,
    is_loading: bool = False,
    on_close: object | None = None,
    disable_animation: bool = False,
    placement: str | None = None,
    parent: QWidget | None = None,
) -> str:
    """弹一条 toast，返回 key（可交给 close_toast 提前关闭）。"""
    return get_toast_provider(parent).add(
        title=title,
        description=description,
        color=color,
        variant=variant,
        radius=radius,
        shadow=shadow,
        severity=severity,
        icon=icon,
        hide_icon=hide_icon,
        hide_close_button=hide_close_button,
        end_content=end_content,
        timeout=timeout,
        should_show_timeout_progress=should_show_timeout_progress,
        is_loading=is_loading,
        on_close=on_close,
        disable_animation=disable_animation,
        placement=placement,
    )


def close_toast(key: str):
    """按 key 关闭单条 toast（走退出动画）。"""
    provider = _key_owners.get(key)
    if provider is None:
        return
    provider.close(key)


def clear_toasts(window: QWidget | None = None):
    """关闭指定窗口（默认当前活动窗口）上的全部 toast。"""
    if window is None:
        host = _resolve_window(None)
        if host is None:
            return
        provider = _providers.get(host.window())
    else:
        provider = _providers.get(window.window())
    if provider is not None:
        provider.clear()
