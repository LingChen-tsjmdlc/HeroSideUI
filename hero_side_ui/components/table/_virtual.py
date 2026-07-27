"""Table 虚拟化滚动（mixin）。

仅当 ``is_virtualized=True`` 且设了 ``max_height`` 时生效。核心思路：

- 行高统一为 ``_virtual_row_height()``（取 token row_min_height），据此把
  "滚动条位置"换算成"应渲染的首行下标 first_visible"。
- 可视行数 = 视口高 // 行高 + 上下缓冲，交给 _RowRenderer.render_window 渲染。
- grid 顶部/底部 spacer 撑出 total*row_h 的总高，保证滚动条范围正确。
- 滚动 valueChanged → 节流（QTimer.singleShot(0)）后重算窗口，避免每像素重填。

宿主 Table 需提供：_renderer / _scroll / _is_virtualized / _row_order / _size /
_grid_host / _apply_row_states / _sync_header_sort_state / _on_scroll_sticky /
_is_header_sticky。
"""

from __future__ import annotations

from PySide6.QtCore import QTimer

from ...themes import TABLE_SIZES

_VIRTUAL_BUFFER = 4  # 可视区上下各多渲染的缓冲行数


class _VirtualMixin:
    def _virtual_row_height(self) -> int:
        cfg = TABLE_SIZES.get(self._size, TABLE_SIZES["md"])
        h = cfg["compact_padding_y"] * 2 if self._is_compact else cfg["row_min_height"]
        return max(1, int(h))

    def _virtual_viewport_height(self) -> int:
        if self._scroll is not None:
            return max(0, self._scroll.viewport().height())
        return 0

    def _virtual_visible_count(self) -> int:
        vp = self._virtual_viewport_height()
        per = self._virtual_row_height()
        base = (vp // per) + 1 if per > 0 else len(self._row_order)
        return base + _VIRTUAL_BUFFER * 2

    def _render_virtual(self, *, force: bool = False):
        """按当前滚动位置渲染可视窗口。

        force=True 时强制重填（数据/列/主题变动后调用）；否则当"应渲染的窗口
        (first, count, total)"与上次完全一致时跳过——同一行内每像素滚动会触发
        几十次 valueChanged，但真正需要换行内容的只有跨行那一次，去重后省掉绝大
        多数无效重填，是虚拟滚动流畅的关键。
        """
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
        # 节流到下一帧，避免连续滚动每像素重填
        if getattr(self, "_virtual_pending", False):
            return
        self._virtual_pending = True
        QTimer.singleShot(0, self._do_virtual_scroll)

    def _do_virtual_scroll(self):
        self._virtual_pending = False
        if not self._is_virtualized or self._scroll is None:
            return
        self._render_virtual()
        if self._is_header_sticky:
            self._on_scroll_sticky(self._scroll.verticalScrollBar().value())
