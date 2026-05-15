"""Textarea 几何/绝对槽/grip drag mixin（私有）。

负责：
- ``resizeEvent`` / ``showEvent`` 时的子部件重摆
- 绝对定位槽（``center_right`` / ``bottom_right``）的几何同步
- 手动 ``_ResizeGrip`` 拖拽产生的高度调整
- absolute spacer 宽度计算（避免双槽重叠）
"""

from ...themes import TEXTAREA_SIZES

from PySide6.QtCore import QPoint, Qt


class _TextareaLayoutMixin:
    """Textarea 几何/绝对槽 mixin。"""

    # ============================================================
    # 事件钩子
    # ============================================================
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 宽度变化会影响 wrap → 行数 → 高度
        self._update_textarea_height()
        self._reposition_inside_label()
        self._reposition_absolute_holders()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_textarea_height()
        self._reposition_inside_label()
        self._reposition_absolute_holders()

    # ============================================================
    # 绝对定位槽（center_right / bottom_right）的实时重摆
    # ============================================================
    def _refresh_abs_spacer_width(self):
        """计算 _abs_spacer 应占的宽度，让 inner 在 layout 里给绝对定位槽让出空间。

        center_right / bottom_right 是绝对定位 holder（不在 wrapper layout 里），
        layout 不知道它们存在，inner 会撑满到 wrapper 右内边距 → 文字 wrap 撞按钮。
        修复：spacer 在 layout 里"代替"它们占位。

        ⚠️ 减去已在 layout 里占位的部分：
          - top_right_slot 已经在 layout 里给 top_right_content 让位
          - clear_btn 已经在 layout 里给清除按钮让位
          - layout spacing (8px) 已经在 _inner 和 top_right_slot 之间留出空隙
          这些"已让位"的宽度落在 wrapper 右侧的同一 X 范围内，所以 spacer 只需要补
          "绝对定位 holder 总宽度 - 已让位部分"，否则会重复让位（双槽时尤其明显）。
        """
        gap = 3  # 文字与按钮之间的最小呼吸间距（不可调，跟 input 的 padding_x 配合）

        # 绝对定位 holder 需要的总让位宽度
        abs_need = 0
        if self._center_right_content is not None:
            self._center_right_holder.adjustSize()
            abs_need = max(abs_need, self._center_right_holder.width()
                           + int(self._center_right_offset))
        if self._bottom_right_content is not None:
            self._bottom_right_holder.adjustSize()
            right_off, _ = self._bottom_right_offset
            abs_need = max(abs_need, self._bottom_right_holder.width()
                           + int(right_off))

        # layout 里已经让出的右侧宽度（top_right_slot + clear_btn + 它们各自的 spacing）
        layout_already_reserved = 0
        wrap_layout = self._wrapper.layout()
        wrap_spacing = wrap_layout.spacing() if wrap_layout else 0
        if self._top_right_content is not None and self._top_right_slot.isVisible():
            self._top_right_slot.adjustSize()
            layout_already_reserved += self._top_right_slot.width() + wrap_spacing
        if self._is_clearable and not self._is_disabled and not self._is_readonly:
            # clear_btn 显隐由淡入淡出控制，但 widget 始终在 layout 里、占着 size
            cw = self._clear_btn.width() or self._clear_btn.sizeHint().width()
            if cw > 0:
                layout_already_reserved += cw + wrap_spacing

        # spacer 只需要补足"绝对定位需要 - layout 已让出"
        need = max(0, abs_need - layout_already_reserved)
        if need > 0:
            need += gap  # 仅当 spacer 真要占位时才加 gap

        if self._abs_spacer.width() != need:
            self._abs_spacer.setFixedWidth(need)

    def _reposition_absolute_holders(self):
        """根据 wrapper 当前几何，重摆 center_right_holder 和 bottom_right_holder。

        在 wrapper Resize / textarea 高度变化 / show / 内容变更后调用。
        位置规则:
          - center_right: 距 wrapper 右边 `center_right_offset`px，垂直居中
          - bottom_right: 距 wrapper 右/底 `bottom_right_offset` (right_px, bottom_px)
        """
        # 重新算 spacer 宽度（内容/sizeHint 可能已变）
        self._refresh_abs_spacer_width()

        ww = self._wrapper.width()
        wh = self._wrapper.height()

        # center_right
        if self._center_right_content is not None and self._center_right_holder.isVisible():
            self._center_right_holder.adjustSize()
            cw = self._center_right_holder.width()
            ch = self._center_right_holder.height()
            x = max(0, ww - cw - int(self._center_right_offset))
            y = max(0, (wh - ch) // 2)
            self._center_right_holder.move(x, y)
            self._center_right_holder.raise_()

        # bottom_right
        if self._bottom_right_content is not None and self._bottom_right_holder.isVisible():
            self._bottom_right_holder.adjustSize()
            bw = self._bottom_right_holder.width()
            bh = self._bottom_right_holder.height()
            right_off, bottom_off = self._bottom_right_offset
            x = max(0, ww - bw - int(right_off))
            y = max(0, wh - bh - int(bottom_off))
            self._bottom_right_holder.move(x, y)
            self._bottom_right_holder.raise_()

        # resize grip：贴 wrapper 右下角，距右/底 2px
        # 注意：bottom_right_content 存在时 grip 自动隐藏，避免和按钮重叠
        if (self._resize_mode is not None
                and self._bottom_right_content is None):
            self._resize_grip.show()
            gw = self._resize_grip.width()
            gh = self._resize_grip.height()
            self._resize_grip.move(max(0, ww - gw - 2), max(0, wh - gh - 2))
            self._resize_grip.raise_()
        else:
            self._resize_grip.hide()

    # ============================================================
    # 手动拖动 resize：grip drag_delta 信号回调
    # ============================================================
    def _on_grip_drag(self, dx: int, dy: int):
        """grip 拖动 → 调整 wrapper 高度/宽度

        进入 manual_height_mode（self._manual_height 不为 None），
        _update_textarea_height 会优先用此值，绕过 auto-resize。
        """
        if self._resize_mode is None:
            return

        # 取一个最小高度（min_rows 对应的高度）和软上限（屏幕可视范围内）
        size_config = TEXTAREA_SIZES.get(self._size, TEXTAREA_SIZES["md"])
        row_h = self._cached_row_height or self._calc_row_height()
        is_inside = self._label_placement == "inside" and self._has_label()
        pad_top, pad_bottom = self._current_wrapper_paddings(size_config, is_inside)
        label_reserve = size_config["inside_input_top_space"] if is_inside else 0
        min_h = row_h * self._min_rows + pad_top + pad_bottom + label_reserve

        # 当前实际高度作为基准；后续 dy 累加
        cur_h = self._manual_height if self._manual_height is not None else self._wrapper.height()

        if self._resize_mode in ("vertical", "both"):
            new_h = max(min_h, cur_h + dy)
            self._manual_height = new_h
            self._wrapper.setFixedHeight(new_h)
            # 通知绝对槽 + 高度信号
            self._reposition_absolute_holders()
            self.height_changed.emit(new_h, row_h)

        # horizontal/both 暂不实现宽度拖动（textarea 通常 full_width）

    def reset_manual_height(self):
        """清除手动拖动设置的高度，恢复 auto-resize 行为"""
        self._manual_height = None
        self._update_textarea_height()

