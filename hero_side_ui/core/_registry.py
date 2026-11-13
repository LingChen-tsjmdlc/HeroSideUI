"""主题与字体管家共用的组件登记簿（内部模块）。"""

from __future__ import annotations

import warnings
import weakref
from collections.abc import Callable
from typing import Any


class WidgetRegistry:
    """以弱引用登记组件，并向其广播变更。

    组件销毁后自动脱离。广播时 C++ 对象已被删除的组件被静默注销；
    其他异常说明组件自身有问题，每种组件与错误组合只告警一次。
    """

    def __init__(self, owner: str) -> None:
        """创建登记簿。

        Args:
            owner: 持有者名称，用于告警文案，如 ThemeProvider。
        """
        self._owner = owner
        self._widgets: weakref.WeakSet = weakref.WeakSet()
        self._warned: set[tuple[str, str]] = set()

    def add(self, widget: Any) -> None:
        """登记组件。"""
        self._widgets.add(widget)

    def discard(self, widget: Any) -> None:
        """注销组件，未登记时忽略。"""
        self._widgets.discard(widget)

    def clear(self) -> None:
        """清空全部登记。"""
        self._widgets.clear()

    def __contains__(self, widget: Any) -> bool:
        return widget in self._widgets

    def __len__(self) -> int:
        return len(self._widgets)

    def broadcast(self, notify: Callable[[Any], None]) -> None:
        """对每个已登记组件调用 notify。

        Args:
            notify: 接收单个组件的回调。

        Note:
            遍历副本，回调中登记或注销不影响本轮。RuntimeError 视为
            组件的 C++ 对象已销毁并注销；其他异常告警后继续通知其余组件。
        """
        for widget in list(self._widgets):
            self.broadcast_to(widget, notify)

    def broadcast_to(self, widget: Any, notify: Callable[[Any], None]) -> None:
        """只通知单个组件，错误处理与 broadcast 一致。

        Args:
            widget: 目标组件。
            notify: 接收该组件的回调。
        """
        try:
            notify(widget)
        except RuntimeError:
            self._widgets.discard(widget)
        except Exception as exc:
            self._warn_once(widget, exc)

    def _warn_once(self, widget: Any, exc: Exception) -> None:
        """同一组件类型与错误只告警一次。"""
        key = (type(widget).__name__, f"{type(exc).__name__}: {exc}")
        if key in self._warned:
            return
        self._warned.add(key)
        warnings.warn(
            f"{self._owner}: notifying {key[0]} failed with {key[1]}",
            RuntimeWarning,
            stacklevel=3,
        )
