"""Textarea 自适应高度（auto-resize）计算 mixin（私有）。

负责：
- 行高（``_calc_row_height``）
- 内容总行数（``_calc_content_rows``，遍历 doc.block 处理 wrap）
- 高度更新（``_update_textarea_height``，约束在 min_rows..max_rows 之间）
- wrapper padding 取值（取决于 inside/outside label）
"""

from PySide6.QtGui import QFontMetrics

from ...themes import TEXTAREA_SIZES


class _TextareaAutosizeMixin:
    """Textarea 高度计算 mixin。"""

    # ============================================================
    # 高度计算（auto-resize 核心）
    # ============================================================
    def _calc_row_height(self) -> int:
        """根据当前字体度量计算一行的实际像素高度（包含 line spacing）"""
        font = self.text_edit.font()
        fm = QFontMetrics(font)
        # lineSpacing 比 height 多出 leading，更接近 textarea 实际行距
        return fm.lineSpacing()

    def _calc_content_rows(self) -> int:
        """估算当前内容占用的视觉行数（含 wrap）"""
        doc = self.text_edit.document()
        # 使其布局到当前 viewport 宽度下
        viewport_w = self.text_edit.viewport().width()
        if viewport_w > 0:
            doc.setTextWidth(viewport_w)

        # 用 documentLayout 报告的总块数 + 每块的 line count
        total_lines = 0
        block = doc.begin()
        while block.isValid():
            layout = block.layout()
            if layout is not None:
                total_lines += max(1, layout.lineCount())
            else:
                total_lines += 1
            block = block.next()
        return max(1, total_lines)

    def _update_textarea_height(self):
        """根据 minRows/maxRows/disable_autosize 计算并应用高度

        如果用户手动拖动过 grip（self._manual_height 不为 None），优先用该高度，
        绕过 auto-resize 逻辑。调 reset_manual_height() 可恢复 auto-resize。
        """
        row_h = self._calc_row_height()
        self._cached_row_height = row_h
        size_config = TEXTAREA_SIZES.get(self._size, TEXTAREA_SIZES["md"])
        is_inside = self._label_placement == "inside" and self._has_label()

        if self._manual_height is not None:
            # 手动模式：用户拖到的高度优先
            total_h = self._manual_height
        else:
            # auto-resize 模式：按 min/max_rows 算
            if self._disable_autosize:
                target_rows = self._min_rows
            else:
                content_rows = self._calc_content_rows()
                target_rows = max(self._min_rows, min(self._max_rows, content_rows))

            text_area_h = row_h * target_rows
            pad_top, pad_bottom = self._current_wrapper_paddings(size_config, is_inside)
            label_reserve = size_config["inside_input_top_space"] if is_inside else 0
            total_h = text_area_h + pad_top + pad_bottom + label_reserve

        # 应用到 wrapper
        if self._wrapper.height() != total_h:
            self._wrapper.setFixedHeight(total_h)

        # textarea 自身固定高度 = wrapper 高度 - padding - label_reserve（让滚动条只在 maxRows 满时出现）
        # 让 _TextEdit 自己占据 inner 给的剩余空间，不显式 setFixedHeight，
        # 这样它会自动跟随 inner 的 layout —— inner_layout 是 setContentsMargins 把
        # 顶部 label_reserve 让出来后的剩余空间。

        # 触发 height_changed（仅在变化时）
        if total_h != self._last_emitted_height:
            self._last_emitted_height = total_h
            self.height_changed.emit(total_h, row_h)

        # 重新摆 label 位置（高度变了）
        self._reposition_inside_label()

    def _current_wrapper_paddings(self, size_config, is_inside: bool):
        """返回当前 wrapper layout 的上下 padding"""
        pad_y = size_config["inside_padding_y"] if is_inside else size_config["padding_y"]
        return pad_y, pad_y

