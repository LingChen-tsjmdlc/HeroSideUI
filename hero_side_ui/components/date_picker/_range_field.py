"""单边框内渲染 start / end 两组日期段的 DateInput 变体。

HeroUI 的 DateRangePicker 是一个输入框内放两组段（中间夹分隔符），
而不是两个独立的输入框，因此这里以子类方式复用 DateInput 的画布、
浮动 label、样式矩阵与辅助文本，仅把「单状态机」扩展为「双状态机」。
"""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt, Signal

from ..date_input._field_state import DateFieldState
from ..date_input._segment import _DateSegment, _SegmentLiteral
from ..date_input._value import DateTimeValue
from ..date_input.date_input import DateInput

RangeValue = Tuple[Optional[DateTimeValue], Optional[DateTimeValue]]


class _RangeDateField(DateInput):
    """双状态机的日期输入框，段控件通过 ``field`` 属性归属 start / end。

    :param end_value: 结束端初始值
    :param separator: 两组段之间的分隔符文本
    """

    # 类级默认：super().__init__ 期间会调用 _rebuild_segments，
    # 此时实例属性尚未赋值，靠类属性判空退回单组渲染
    _end_state: Optional[DateFieldState] = None
    _separator_text = "–"

    range_changed = Signal(object)

    def __init__(
        self,
        *,
        end_value: Optional[DateTimeValue] = None,
        separator: str = "–",
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._separator_text = separator
        self._end_state = DateFieldState(
            value=end_value,
            placeholder_value=self._state._placeholder,
            granularity=self._granularity,
            hour_cycle=self._hour_cycle,
            locale=self._locale,
            identifier=self._calendar,
            min_value=self._state._min_value,
            max_value=self._state._max_value,
            hide_time_zone=self._hide_time_zone,
            should_force_leading_zeros=self._state._force_zeros,
        )
        self._rebuild_segments()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation(animate=False)

    # ------------------------------------------------------------------
    # 段构建
    # ------------------------------------------------------------------

    def _rebuild_segments(self):
        if self._end_state is None:
            super()._rebuild_segments()
            return

        from ...utils import clear_layout

        self._segment_row.setUpdatesEnabled(False)
        clear_layout(self._segment_layout)
        self._segment_widgets = []
        self._literal_widgets = []

        self._build_group("start", self._state)

        sep = _SegmentLiteral(f" {self._separator_text} ", parent=self._segment_row)
        self._segment_layout.addWidget(sep)
        self._literal_widgets.append(sep)

        self._build_group("end", self._end_state)

        self._refresh_segment_text()
        self._segment_row.setUpdatesEnabled(True)

    def _build_group(self, field: str, state: DateFieldState):
        """把一个状态机的段序渲染进共享的段行。"""
        for spec in state.specs:
            if spec.is_literal:
                lit = _SegmentLiteral(spec.text, parent=self._segment_row)
                self._segment_layout.addWidget(lit)
                self._literal_widgets.append(lit)
                continue

            seg = _DateSegment(
                spec.type,
                min_digits=spec.min_digits,
                on_edit=(
                    lambda st, a, p, f=field: self._on_field_edit(f, st, a, p)
                ),
                on_focus_move=self._on_segment_focus_move,
                on_focus_change=(
                    lambda st, foc, f=field: self._on_field_focus_change(f, st, foc)
                ),
                parent=self._segment_row,
            )
            seg.field = field
            seg.set_editable(spec.is_editable and not self._is_disabled)
            seg.set_readonly(self._is_readonly)
            self._segment_layout.addWidget(seg)
            self._segment_widgets.append(seg)

    def _state_for(self, field: str) -> DateFieldState:
        return self._state if field == "start" else self._end_state

    def _refresh_segment_text(self):
        for seg in self._segment_widgets:
            state = self._state_for(getattr(seg, "field", "start"))
            seg.setText(state.segment_text(seg.seg_type, seg.min_digits))
        self._segment_row.adjustSize()

    # ------------------------------------------------------------------
    # 事件（field 维度）
    # ------------------------------------------------------------------

    def _on_field_edit(self, field: str, seg_type: str, action: str, payload):
        if self._is_readonly or self._is_disabled:
            return

        state = self._state_for(field)
        before = self.range_value()

        if action == "increment":
            state.increment(seg_type, payload)
        elif action == "digit":
            if state.append_digit(seg_type, payload):
                self._advance_focus_in_field(field, seg_type)
        elif action == "clear":
            state.clear_segment(seg_type)
        elif action == "day_period":
            state._set_segment("dayPeriod", payload)

        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation()

        after = self.range_value()
        if after != before:
            self.range_changed.emit(after)

    def _on_field_focus_change(self, field: str, seg_type: str, focused: bool):
        if not focused:
            self._state_for(field).commit_segment(seg_type)
            self._refresh_segment_text()

        any_focused = any(s.hasFocus() for s in self._segment_widgets)
        was_focused = self._is_focused
        self._is_focused = any_focused

        if any_focused != was_focused:
            self._update_label_animation()
            if self._variant == "underlined":
                if any_focused:
                    self._underline.expand()
                else:
                    self._underline.collapse()

        self._apply_styles()

    def _advance_focus_in_field(self, field: str, seg_type: str):
        """段输满后跳到下一个可编辑段（跨 field 时自然进入 end 组）。"""
        segs = self._editable_segments()
        idx = next(
            (
                i
                for i, s in enumerate(segs)
                if s.seg_type == seg_type and getattr(s, "field", "start") == field
            ),
            None,
        )
        if idx is not None and idx + 1 < len(segs):
            segs[idx + 1].setFocus(Qt.FocusReason.TabFocusReason)

    def _sync_invalid_from_state(self):
        if self._end_state is None:
            super()._sync_invalid_from_state()
            return
        if self._explicit_invalid():
            return
        self._is_invalid = (
            self._state.is_invalid()
            or self._end_state.is_invalid()
            or self._is_reversed()
        )

    def _is_reversed(self) -> bool:
        """结束早于开始时视为无效。"""
        start, end = self._state.value(), self._end_state.value()
        if start is None or end is None:
            return False
        return (end.year, end.month, end.day) < (start.year, start.month, start.day)

    def _recreate_state(self):
        """locale / granularity 变化时两个状态机都要重建。"""
        end_current = self._end_state.value() if self._end_state else None
        super()._recreate_state()
        if self._end_state is None:
            return
        self._end_state = DateFieldState(
            value=end_current,
            placeholder_value=self._state._placeholder,
            granularity=self._granularity,
            hour_cycle=self._hour_cycle,
            locale=self._locale,
            identifier=self._calendar,
            min_value=self._state._min_value,
            max_value=self._state._max_value,
            hide_time_zone=self._hide_time_zone,
            should_force_leading_zeros=self._state._force_zeros,
        )
        self._rebuild_segments()
        self._apply_styles()

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def range_value(self) -> RangeValue:
        end = self._end_state.value() if self._end_state else None
        return (self._state.value(), end)

    def set_range_value(self, value: RangeValue):
        start, end = value
        self._state.set_value(start)
        if self._end_state is not None:
            self._end_state.set_value(end)
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation()
        self.range_changed.emit(self.range_value())

    def clear(self):
        self._state.clear()
        if self._end_state is not None:
            self._end_state.clear()
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation()
        self.range_changed.emit(self.range_value())
