"""HeroSideUI DateInput Component — 分段日期输入。

基于 HeroUI v2 的 DateInput 设计。外框视觉与 Input 同源（复用
`input/_wrapper.py` 的画布与配色决策），内部把 QLineEdit 换成一排
可独立聚焦的段（月/日/年/时/分/秒/AM-PM/时区）。

子模块：
    - ``_value``       → 值原语 DateTimeValue 与解析函数
    - ``_pattern``     → 由 ICU 推导段顺序
    - ``_field_state`` → 段编辑状态机
    - ``_segment``     → 单个段控件
    - ``_styling``     → 样式计算
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...animation import LabelFloatAnimation, UnderlineBar
from ...core import ThemeProvider
from ...themes import DATE_INPUT_SIZES
from ..input._layout import _InputLayoutMixin
from ..input._wrapper import _InputWrapper
from ..text import Text
from ._field_state import DateFieldState
from ._pattern import VALID_GRANULARITIES
from ._segment import _DateSegment, _SegmentLiteral
from ._styling import _DateInputStylingMixin
from ._value import DateTimeValue


class DateInput(_DateInputStylingMixin, _InputLayoutMixin, QWidget):
    """HeroUI 风格的分段日期输入组件。"""

    value_changed = Signal(object)

    def __init__(
        self,
        label: str = "",
        value: Optional[DateTimeValue] = None,
        placeholder_value: Optional[DateTimeValue] = None,
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: Optional[str] = None,
        label_placement: str = "inside",
        granularity: str = "day",
        hour_cycle: Optional[int] = None,
        hide_time_zone: bool = False,
        should_force_leading_zeros: bool = True,
        min_value: Optional[DateTimeValue] = None,
        max_value: Optional[DateTimeValue] = None,
        locale: str = "en_US",
        calendar: str = "gregorian",
        is_disabled: bool = False,
        is_invalid: bool = False,
        is_required: bool = False,
        is_readonly: bool = False,
        full_width: bool = True,
        description: str = "",
        error_message: str = "",
        start_content=None,
        end_content=None,
        on_start_content_click=None,
        on_end_content_click=None,
        theme: str = "auto",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        if granularity not in VALID_GRANULARITIES:
            raise ValueError(
                f"invalid granularity: {granularity!r}, "
                f"expected one of {VALID_GRANULARITIES}"
            )

        # ---- 状态 ----
        self._label_text = label
        self._variant = variant
        self._color = color
        self._size = size
        self._radius = radius
        self._label_placement = label_placement
        self._granularity = granularity
        self._hour_cycle = hour_cycle
        self._hide_time_zone = hide_time_zone
        self._locale = locale
        self._calendar = calendar
        self._is_disabled = is_disabled
        self._is_required = is_required
        self._is_readonly = is_readonly
        self._full_width = full_width
        self._description = description
        self._error_message = error_message
        self._start_content = start_content
        self._end_content = end_content
        self._on_start_click = on_start_content_click
        self._on_end_click = on_end_content_click
        self._theme_mode = theme
        self._theme = self._resolve_theme(theme)

        self._is_hover = False
        self._is_focused = False
        self._user_width_locked = False

        # ---- 段状态机 ----
        self._state = DateFieldState(
            value=value,
            placeholder_value=placeholder_value,
            granularity=granularity,
            hour_cycle=hour_cycle,
            locale=locale,
            identifier=calendar,
            min_value=min_value,
            max_value=max_value,
            hide_time_zone=hide_time_zone,
            should_force_leading_zeros=should_force_leading_zeros,
        )
        # 越界的初始值本身就该显示为 invalid，不能只看外部传参
        self._is_invalid = is_invalid or self._state.is_invalid()

        self._segment_widgets: List[_DateSegment] = []
        self._literal_widgets: List[_SegmentLiteral] = []

        self._setup_ui()
        self._rebuild_segments()
        self._bind_events()
        self._apply_styles()
        self._update_label_animation(animate=False)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)

    # ============================================================
    # UI 结构
    # ============================================================
    def _setup_ui(self):
        self.setObjectName("heroDateInput")

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

        # outside / outside-top 的静态 label
        self._outside_label = Text(self._label_text, weight="medium", selectable=False)
        self._outside_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._outside_label.setTextFormat(Qt.TextFormat.RichText)
        self._root.addWidget(self._outside_label, 0, Qt.AlignmentFlag.AlignLeft)

        # outside-left 的横向行
        self._outside_left_row = QWidget(self)
        _row = QHBoxLayout(self._outside_left_row)
        _row.setContentsMargins(0, 0, 0, 0)
        _row.setSpacing(8)

        self._outside_left_label = Text(
            self._label_text, weight="medium", selectable=False
        )
        self._outside_left_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._outside_left_label.setTextFormat(Qt.TextFormat.RichText)
        _row.addWidget(
            self._outside_left_label,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )

        # 背景画布（与 Input 同一个 wrapper 实现）
        self._wrapper = _InputWrapper(self._outside_left_row)
        wrap_layout = QHBoxLayout(self._wrapper)
        wrap_layout.setContentsMargins(12, 6, 12, 6)
        wrap_layout.setSpacing(8)

        self._start_slot = QWidget(self._wrapper)
        self._start_slot_layout = QHBoxLayout(self._start_slot)
        self._start_slot_layout.setContentsMargins(0, 0, 0, 0)
        self._start_slot_layout.setSpacing(0)
        self._start_slot.hide()
        wrap_layout.addWidget(self._start_slot, 0, Qt.AlignmentFlag.AlignVCenter)

        # 段容器
        self._inner = QWidget(self._wrapper)
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)

        self._segment_row = QWidget(self._inner)
        self._segment_layout = QHBoxLayout(self._segment_row)
        self._segment_layout.setContentsMargins(0, 0, 0, 0)
        self._segment_layout.setSpacing(0)
        self._segment_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._inner_layout.addWidget(self._segment_row)

        wrap_layout.addWidget(self._inner, 1)

        self._end_slot = QWidget(self._wrapper)
        self._end_slot_layout = QHBoxLayout(self._end_slot)
        self._end_slot_layout.setContentsMargins(0, 0, 0, 0)
        self._end_slot_layout.setSpacing(0)
        self._end_slot.hide()
        wrap_layout.addWidget(self._end_slot, 0, Qt.AlignmentFlag.AlignVCenter)

        self._underline = UnderlineBar(parent=self._wrapper)
        self._underline.hide()

        _row.addWidget(self._wrapper, 1)
        self._root.addWidget(self._outside_left_row)

        # 浮动 label（inside / outside 两种 placement 共用）
        self._inside_label = Text(self._label_text, parent=self, selectable=False)
        self._inside_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._inside_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._inside_label.raise_()

        # helper 区
        self._helper_label = Text("", weight="normal", selectable=False)
        self._helper_label.setWordWrap(True)
        self._helper_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._helper_label.hide()
        self._root.addWidget(self._helper_label)

        # parent=self 让动画随组件一起销毁；否则组件已析构、动画仍在跑，
        # 回调里访问 self._wrapper 会撞上已删除的 C++ 对象。
        self._label_anim = LabelFloatAnimation(
            on_progress=self._on_label_progress, duration=200, parent=self
        )
        self._label_color_resting = QColor("#a1a1aa")
        self._label_color_floated = QColor("#71717a")

        self._relayout_for_label_placement()

    # ============================================================
    # 段的构建与刷新
    # ============================================================
    def _rebuild_segments(self):
        """按当前段序重建段控件（locale/granularity 变化时调用）。"""
        from ...utils import clear_layout

        self._segment_row.setUpdatesEnabled(False)
        clear_layout(self._segment_layout)
        self._segment_widgets = []
        self._literal_widgets = []

        for spec in self._state.specs:
            if spec.is_literal:
                lit = _SegmentLiteral(spec.text, parent=self._segment_row)
                self._segment_layout.addWidget(lit)
                self._literal_widgets.append(lit)
                continue

            seg = _DateSegment(
                spec.type,
                min_digits=spec.min_digits,
                on_edit=self._on_segment_edit,
                on_focus_move=self._on_segment_focus_move,
                on_focus_change=self._on_segment_focus_change,
                parent=self._segment_row,
            )
            # 时区段是纯展示，不可编辑
            seg.set_editable(spec.is_editable and not self._is_disabled)
            seg.set_readonly(self._is_readonly)
            self._segment_layout.addWidget(seg)
            self._segment_widgets.append(seg)

        self._refresh_segment_text()
        self._segment_row.setUpdatesEnabled(True)

    def _refresh_segment_text(self):
        """把状态机里的段值写回各段控件。"""
        for seg in self._segment_widgets:
            seg.setText(self._state.segment_text(seg.seg_type, seg.min_digits))
        # 段宽随文本变化，重新摆放浮动 label 与最小宽度
        self._segment_row.adjustSize()

    # ============================================================
    # 事件
    # ============================================================
    def _bind_events(self):
        self._wrapper.installEventFilter(self)
        self._wrapper.setMouseTracking(True)
        self._wrapper.mousePressEvent = self._on_wrapper_clicked
        self._inside_label.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self._wrapper:
            if event.type() == QEvent.Type.Enter:
                self._is_hover = True
                self._apply_styles()
            elif event.type() == QEvent.Type.Leave:
                self._is_hover = False
                self._apply_styles()
        elif obj is self._inside_label:
            if event.type() == QEvent.Type.MouseButtonPress:
                self._focus_first_segment()
                return True
        return super().eventFilter(obj, event)

    def _on_wrapper_clicked(self, event):
        self._focus_first_segment()
        QFrame.mousePressEvent(self._wrapper, event)

    def _focus_first_segment(self):
        for seg in self._segment_widgets:
            if seg.focusPolicy() != Qt.FocusPolicy.NoFocus:
                seg.setFocus(Qt.FocusReason.MouseFocusReason)
                return

    def _editable_segments(self) -> List[_DateSegment]:
        return [
            s
            for s in self._segment_widgets
            if s.focusPolicy() != Qt.FocusPolicy.NoFocus
        ]

    def _on_segment_focus_move(self, direction: int):
        """左右键在可编辑段之间移动焦点。"""
        segs = self._editable_segments()
        if not segs:
            return
        focused = next((i for i, s in enumerate(segs) if s.hasFocus()), None)
        if focused is None:
            segs[0].setFocus(Qt.FocusReason.TabFocusReason)
            return
        target = focused + direction
        if 0 <= target < len(segs):
            segs[target].setFocus(Qt.FocusReason.TabFocusReason)

    def _on_segment_focus_change(self, seg_type: str, focused: bool):
        """段获得/失去焦点：同步整体 focus 状态与段视觉。"""
        if not focused:
            # 离开时提交该段，把中间值夹进合法范围
            self._state.commit_segment(seg_type)
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

    def _on_segment_edit(self, seg_type: str, action: str, payload):
        """段控件上报的键盘动作 → 状态机 → 刷新文本 → 发信号。"""
        if self._is_readonly or self._is_disabled:
            return

        before = self._state.value()

        if action == "increment":
            self._state.increment(seg_type, payload)
        elif action == "digit":
            filled = self._state.append_digit(seg_type, payload)
            if filled:
                self._advance_focus_from(seg_type)
        elif action == "clear":
            self._state.clear_segment(seg_type)
        elif action == "day_period":
            self._state._set_segment("dayPeriod", payload)

        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation()

        after = self._state.value()
        if after != before:
            self.value_changed.emit(after)

    def _advance_focus_from(self, seg_type: str):
        """某段输满后自动跳到下一个可编辑段。"""
        segs = self._editable_segments()
        idx = next((i for i, s in enumerate(segs) if s.seg_type == seg_type), None)
        if idx is not None and idx + 1 < len(segs):
            segs[idx + 1].setFocus(Qt.FocusReason.TabFocusReason)

    def _sync_invalid_from_state(self):
        """值越界时自动进入 invalid 视觉（不覆盖用户显式设的 True）。"""
        if self._explicit_invalid():
            return
        self._is_invalid = self._state.is_invalid()

    def _explicit_invalid(self) -> bool:
        return getattr(self, "_user_invalid", False)

    # ============================================================
    # 公共 API
    # ============================================================
    def value(self) -> Optional[DateTimeValue]:
        """当前值；有段未填时返回 None。"""
        return self._state.value()

    def set_value(self, value: Optional[DateTimeValue]):
        self._state.set_value(value)
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation()
        self.value_changed.emit(self._state.value())

    def clear(self):
        """清空所有段，回到占位态。"""
        self._state.clear()
        self._refresh_segment_text()
        self._apply_styles()
        self._update_label_animation()
        self.value_changed.emit(None)

    def set_granularity(self, granularity: str):
        if granularity not in VALID_GRANULARITIES:
            raise ValueError(f"invalid granularity: {granularity!r}")
        self._granularity = granularity
        self._recreate_state()

    def set_hour_cycle(self, hour_cycle: Optional[int]):
        self._hour_cycle = hour_cycle
        self._recreate_state()

    def set_hide_time_zone(self, hide: bool):
        self._hide_time_zone = hide
        self._recreate_state()

    def set_locale(self, locale: str):
        self._locale = locale
        self._recreate_state()

    def set_calendar(self, calendar: str):
        self._calendar = calendar
        self._recreate_state()

    def set_min_value(self, value: Optional[DateTimeValue]):
        self._state._min_value = value
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()

    def set_max_value(self, value: Optional[DateTimeValue]):
        self._state._max_value = value
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()

    def _recreate_state(self):
        """段序相关属性变化 → 重建状态机并重建段控件，保留已有值。"""
        current = self._state.value()
        self._state = DateFieldState(
            value=current,
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

    def set_label(self, label: str):
        self._label_text = label
        self._apply_styles()
        self._update_label_animation()

    def set_color(self, color: str):
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        self._variant = variant
        self._apply_styles()

    def set_size(self, size: str):
        self._size = size
        self._apply_styles()

    def set_radius(self, radius: Optional[str]):
        self._radius = radius
        self._apply_styles()

    def set_label_placement(self, placement: str):
        self._label_placement = placement
        self._relayout_for_label_placement()
        self._apply_styles()
        self._update_label_animation()

    def is_disabled(self) -> bool:
        return self._is_disabled

    def set_is_disabled(self, disabled: bool):
        self._is_disabled = disabled
        for seg in self._segment_widgets:
            spec_editable = seg.seg_type != "timeZone"
            seg.set_editable(spec_editable and not disabled)
        self._apply_styles()

    def set_is_invalid(self, invalid: bool):
        self._user_invalid = invalid
        self._is_invalid = invalid
        self._apply_styles()

    def set_is_required(self, required: bool):
        self._is_required = required
        self._apply_styles()

    def set_is_readonly(self, readonly: bool):
        self._is_readonly = readonly
        for seg in self._segment_widgets:
            seg.set_readonly(readonly)
        self._apply_styles()

    def set_description(self, description: str):
        self._description = description
        self._apply_styles()

    def set_error_message(self, message: str):
        self._error_message = message
        self._apply_styles()

    def set_start_content(self, content, on_click=None):
        self._start_content = content
        if on_click is not None:
            self._on_start_click = on_click
        self._apply_styles()

    def set_end_content(self, content, on_click=None):
        self._end_content = content
        if on_click is not None:
            self._on_end_click = on_click
        self._apply_styles()

    # ============================================================
    # 宽度接管
    # ============================================================
    def setFixedWidth(self, w: int):  # noqa: N802
        self._user_width_locked = True
        super().setFixedWidth(w)
        self._apply_styles()

    def setMinimumWidth(self, w: int):  # noqa: N802
        self._user_width_locked = True
        super().setMinimumWidth(w)
        self._apply_styles()

    def setMaximumWidth(self, w: int):  # noqa: N802
        self._user_width_locked = True
        super().setMaximumWidth(w)
        self._apply_styles()

    def set_width(self, w: int):
        self.setFixedWidth(w)

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        if theme == "auto":
            self._theme_mode = "auto"
            self._theme = self._resolve_theme("auto")
            ThemeProvider.instance().register(self)
        else:
            if self._theme_mode == "auto":
                ThemeProvider.instance().unregister(self)
            self._theme_mode = theme
            self._theme = theme
        self._apply_styles()

    def _apply_provider_theme(self, theme: str):
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # 状态查询（供 Input 的 mixin 复用）
    # ============================================================
    def _has_label(self) -> bool:
        return bool(self._label_text)

    def _has_value(self) -> bool:
        return self._state.has_any_input()

    def _filled_within(self) -> bool:
        """label 是否该浮起。

        DateInput 的段永远渲染占位符（mm/dd/yyyy），内容区从不为空，
        所以 label 必须恒定浮起——否则会压在段文字上。这与 Input
        「空值时 label 落回中央」的行为不同。
        """
        return True

    def _update_label_animation(self, animate: bool = True):
        if self._label_placement not in ("inside", "outside"):
            return
        if not self._has_label():
            return
        self._label_anim.set_state(self._filled_within(), animate=animate)


__all__ = ["DateInput"]
