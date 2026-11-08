"""Table 虚拟化滚动 mixin：行高统一 + spacer 撑总高 + 窗口去重重填。"""

from __future__ import annotations

from PySide6.QtCore import QTimer

from ...themes import TABLE_SIZES

_VIRTUAL_BUFFER = 4  # 可视区上下各多渲染的缓冲行数


class _VirtualMixin:
    """表格虚拟化滚动 mixin，用统一行高与 spacer 撑起总高。"""

    def _virtual_row_height(self) -> int:
        """返回虚拟化使用的统一行高。"""
        cfg = TABLE_SIZES.get(self._size, TABLE_SIZES["md"])
        h = cfg["compact_padding_y"] * 2 if self._is_compact else cfg["row_min_height"]
        return max(1, int(h))

    def _virtual_viewport_height(self) -> int:
        """返回滚动区视口高度，无滚动区时返回 0。"""
        if self._scroll is not None:
            return max(0, self._scroll.viewport().height())
        return 0

    def _virtual_visible_count(self) -> int:
        """返回带上下缓冲的可视行数。"""
        vp = self._virtual_viewport_height()
        per = self._virtual_row_height()
        base = (vp // per) + 1 if per > 0 else len(self._row_order)
        return base + _VIRTUAL_BUFFER * 2

    def _render_virtual(self, *, force: bool = False):
        """按滚动位置渲染可视窗口；窗口不变时跳过重填（流畅关键）。"""
        total = len(self._row_order)
        per = self._virtual_row_height()
        sb = self._scroll.verticalScrollBar() if self._scroll else None
        scroll_val = sb.value() if sb is not None else 0
        first = max(0, scroll_val // per - _VIRTUAL_BUFFER)
        count = self._virtual_visible_count()
        first = min(first, max(0, total - 1))
        window = (first, count, total)
        if not force and window == getattr(self, "_virtual_window", None):
            return
        self._virtual_window = window
        self._renderer.render_window(first, count, total)
        self._apply_row_states(animated=False)
        self._sync_header_sort_state()

    def _on_virtual_scroll(self, _value: int):
        """把连续滚动节流到下一帧再重填窗口。

        Args:
            _value: 滚动条位置，本实现不读取。

        Note:
            用 _virtual_pending 去重，避免连续滚动每像素触发重填。
        """
        # 节流到下一帧，避免连续滚动每像素重填
        if getattr(self, "_virtual_pending", False):
            return
        self._virtual_pending = True
        QTimer.singleShot(0, self._do_virtual_scroll)

    def _do_virtual_scroll(self):
        """执行节流后的窗口重填并同步吸顶表头。

        Note:
            未启用虚拟化或无滚动区时直接返回。
        """
        self._virtual_pending = False
        if not self._is_virtualized or self._scroll is None:
            return
        self._render_virtual()
        if self._is_header_sticky:
            self._on_scroll_sticky(self._scroll.verticalScrollBar().value())
