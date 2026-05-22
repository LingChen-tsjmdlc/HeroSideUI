"""Tooltip 顶层模式滚动跟随 mixin。

为什么独立：tooltip.py 已超 800 行红线，把"顶层 Qt.Tool tooltip 跟随父滚动"
这套（连接祖先 scrollbar.valueChanged + 节流重定位）剥出来。embedded 模式不需要
这套——子 widget 跟随父体系滚动是 Qt 原生能力。

为什么用 valueChanged 而非自定义 SmoothScroll 信号：
    valueChanged 是 Qt 原生信号，对所有滚动来源（鼠标滚轮 / 拖动 scrollbar /
    键盘 PageDown / scrollTo() API / SmoothScroll 动画的逐帧 setValue）都生效；
    与 SmoothScroll 解耦，零依赖。
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QAbstractScrollArea, QWidget

__all__ = ["_TooltipScrollFollowMixin"]


class _TooltipScrollFollowMixin:
    """Tooltip 顶层模式下"滚动跟随"逻辑（已有 _scroll_bars / _scroll_reposition_pending
    / _trigger / _is_open / _refresh_geometry 由 Tooltip 自己提供）。

    embedded 模式下宿主类**不调用**这些方法（子 widget 自动跟随）。
    """

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
