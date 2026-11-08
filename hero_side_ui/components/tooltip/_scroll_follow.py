"""Tooltip 顶层模式滚动跟随 mixin：连接祖先 scrollbar valueChanged + 节流重定位
（embedded 模式不需要，Qt 原生跟随）。
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QAbstractScrollArea, QWidget

__all__ = ["_TooltipScrollFollowMixin"]


class _TooltipScrollFollowMixin:
    """顶层模式滚动跟随逻辑；embedded 模式宿主不调用这些方法。"""

    def _connect_scroll_watchers(self, trigger: QWidget) -> None:
        """沿 trigger 祖先链找所有 QAbstractScrollArea，连接 scrollbar.valueChanged。"""
        self._disconnect_scroll_watchers()
        w = trigger
        seen = set()
        while w is not None:
            if isinstance(w, QAbstractScrollArea):
                for bar in (w.verticalScrollBar(), w.horizontalScrollBar()):
                    if bar is not None and id(bar) not in seen:
                        seen.add(id(bar))
                        bar.valueChanged.connect(self._on_scroll_detected)  # type: ignore[attr-defined]
                        self._scroll_bars.append(bar)  # type: ignore[attr-defined]
            w = w.parentWidget()

    def _disconnect_scroll_watchers(self) -> None:
        """断开所有已连接的滚动条监听并清空记录。"""
        for bar in self._scroll_bars:  # type: ignore[attr-defined]
            try:
                bar.valueChanged.disconnect(self._on_scroll_detected)  # type: ignore[attr-defined]
            except (RuntimeError, TypeError):
                pass
        self._scroll_bars.clear()  # type: ignore[attr-defined]

    def _on_scroll_detected(self, _value: int) -> None:
        """祖先 scroll area 滚动 → 节流到下一帧重新定位（多 scrollbar 同帧合并）。"""
        if not self._is_open:  # type: ignore[attr-defined]
            return
        # fade-out 期间不 reposition：tooltip 本来就要消失，重定位反而会让位置在
        # 关闭动画中跳动；用户若 reopen 会触发 _do_open 走 reopening 重算位置。
        if getattr(self, "_closing", False):
            return
        if self._scroll_reposition_pending:  # type: ignore[attr-defined]
            return
        self._scroll_reposition_pending = True  # type: ignore[attr-defined]
        QTimer.singleShot(0, self._do_scroll_reposition)

    def _do_scroll_reposition(self) -> None:
        """实际重算 tooltip 位置（复用已有 _refresh_geometry）。"""
        self._scroll_reposition_pending = False  # type: ignore[attr-defined]
        if not self._is_open or self._trigger is None:  # type: ignore[attr-defined]
            return
        try:
            self._refresh_geometry()  # type: ignore[attr-defined]
        except RuntimeError:
            return
