"""_RangeDateField：单边框内两组日期段（夹分隔符），复用 DateInput 画布。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal

from ..date_input._field_state import DateFieldState
from ..date_input._segment import _DateSegment, _SegmentLiteral
from ..date_input._value import DateTimeValue
from ..date_input.date_input import DateInput

RangeValue = tuple[DateTimeValue | None, DateTimeValue | None]


class _RangeDateField(DateInput):
    """双状态机日期输入框，段经 field 属性归属 start/end。

    Args:
        end_value: 结束端初始值。
        separator: 两组段之间的分隔符。
    """

    # 类级默认：super().__init__ 期间会调用 _rebuild_segments，
    # 此时实例属性尚未赋值，靠类属性判空退回单组渲染
    _end_state: DateFieldState | None = None
    _separator_text = "–"

    range_changed = Signal(object)

    def __init__(
        self,
        *,
        end_value: DateTimeValue | None = None,
        separator: str = "–",
        **kwargs,
    ):
        """创建双端日期段输入框。

        Args:
            end_value: 结束端初始值。
            separator: 两组段之间的分隔符文本。
            **kwargs: 透传给 DateInput 的构造参数。

        Note:
            类级默认的 _end_state=None 用于 super().__init__ 期间——
            那时实例属性尚未赋值，_rebuild_segments 会退回单组渲染；
            构造末尾再建 end 状态机并重建段。
        """
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
        """按 start / 分隔符 / end 的顺序重建两组段控件。

        Note:
            end 状态机尚未建立时（super 构造期）退回基类单组渲染。
        """
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
        """把一个状态机的段序渲染进共享的段行。

        Args:
            field: 归属标识 start / end，写在段控件的 field 属性上。
            state: 该端对应的 DateFieldState。

        Note:
            回调通过默认参数捕获 field，避免循环变量晚绑定。
        """
        for spec in state.specs:
            if spec.is_literal:
                lit = _SegmentLiteral(spec.text, parent=self._segment_row)
                self._segment_layout.addWidget(lit)
                self._literal_widgets.append(lit)
                continue

            seg = _DateSegment(
                spec.type,
                min_digits=spec.min_digits,
                on_edit=(lambda st, a, p, f=field: self._on_field_edit(f, st, a, p)),
                on_focus_move=self._on_segment_focus_move,
                on_focus_change=(lambda st, foc, f=field: self._on_field_focus_change(f, st, foc)),
                parent=self._segment_row,
            )
            seg.field = field
            seg.set_editable(spec.is_editable and not self._is_disabled)
            seg.set_readonly(self._is_readonly)
            self._segment_layout.addWidget(seg)
            self._segment_widgets.append(seg)

    def _state_for(self, field: str) -> DateFieldState:
        """按归属标识取状态机。

        Args:
            field: start / end。

        Returns:
            对应端的 DateFieldState。
        """
        return self._state if field == "start" else self._end_state

    def _refresh_segment_text(self):
        """按各段的 field 归属把两个状态机的值写回段控件。"""
        for seg in self._segment_widgets:
            state = self._state_for(getattr(seg, "field", "start"))
            seg.setText(state.segment_text(seg.seg_type, seg.min_digits))
        self._segment_row.adjustSize()

    # ------------------------------------------------------------------
    # 事件（field 维度）
    # ------------------------------------------------------------------

    def _on_field_edit(self, field: str, seg_type: str, action: str, payload):
        """按 field 路由段编辑动作 → 对应状态机 → 刷新 → 发 range_changed。

        Args:
            field: 归属标识 start / end。
            seg_type: 段类型。
            action: increment / digit / clear / day_period。
            payload: 动作参数。

        Note:
            只读或禁用直接忽略；只有范围真的变化才发信号。
        """
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
        """段焦点变化：提交对应端段值并同步整体 focus 状态。

        Args:
            field: 归属标识 start / end。
            seg_type: 段类型。
            focused: True 表示获得焦点。

        Note:
            underlined 变体在整体焦点切换时展开 / 收起下划线。
        """
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
        """段输满后跳到下一个可编辑段（跨 field 时自然进入 end 组）。

        Args:
            field: 当前归属标识。
            seg_type: 刚输满的段类型。
        """
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
        """两端任一越界或范围倒置时自动进入 invalid 视觉。

        Note:
            end 状态机未建立时退回基类逻辑；用户显式设的 True 优先。
        """
        if self._end_state is None:
            super()._sync_invalid_from_state()
            return
        if self._explicit_invalid():
            return
        self._is_invalid = (
            self._state.is_invalid() or self._end_state.is_invalid() or self._is_reversed()
        )

    def _is_reversed(self) -> bool:
        """结束早于开始时视为无效。

        Returns:
            两端都填好且 end 日期早于 start 时为 True。
        """
        start, end = self._state.value(), self._end_state.value()
        if start is None or end is None:
            return False
        return (end.year, end.month, end.day) < (start.year, start.month, start.day)

    def _recreate_state(self):
        """locale / granularity 变化时两个状态机都要重建并保留各自的值。"""
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
        """返回 (start, end) 当前值。

        Returns:
            两端值对象；任一端未填完则为 None。
        """
        end = self._end_state.value() if self._end_state else None
        return (self._state.value(), end)

    def set_range_value(self, value: RangeValue):
        """受控设置范围并发 range_changed。

        Args:
            value: (start, end) 元组；元素可为 None。
        """
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
        """清空两端全部段并发出 range_changed。"""
        self._state.clear()
        if self._end_state is not None:
            self._end_state.clear()
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation()
        self.range_changed.emit(self.range_value())
