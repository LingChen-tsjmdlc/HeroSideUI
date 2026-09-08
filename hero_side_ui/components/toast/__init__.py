"""Toast 轻提示组件（HeroUI v2 toast）。

- ``Toast``         单张卡片（icon + title/description + 关闭按钮 + 倒计时进度）
- ``ToastRegion``   宿主窗口内的堆叠区（定位 / 折叠展开 / 进出场）
- ``ToastProvider`` 挂在窗口上的队列入口
- ``add_toast`` / ``close_toast`` / ``clear_toasts`` 全局快捷函数
"""

from ._provider import (
    ToastProvider,
    add_toast,
    clear_toasts,
    close_toast,
    configure_toasts,
    get_toast_provider,
)
from ._region import ToastRegion
from .toast import Toast

__all__ = [
    "Toast",
    "ToastRegion",
    "ToastProvider",
    "add_toast",
    "close_toast",
    "clear_toasts",
    "configure_toasts",
    "get_toast_provider",
]
