"""DateInput 分段日期输入：外框复用 Input 决策，内部为可聚焦段列表。

子模块：_value/_pattern/_field_state/_segment/_styling。
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ..._shared.dates import VALID_GRANULARITIES, DateFieldState, DateTimeValue
from ..._shared.fields import InputLayoutMixin, InputWrapper
from ...animation import LabelFloatAnimation, UnderlineBar
from ...core import FontProvider, ThemeProvider
from ..text import Text
from ._segment import _DateSegment, _SegmentLiteral
from ._styling import _DateInputStylingMixin


class DateInput(_DateInputStylingMixin, InputLayoutMixin, QWidget):
    """HeroUI 风格分段日期输入。

    供子类覆写的类属性：_object_name、_valid_granularities、
    _default_granularity、_include_date（TimeInput 即由此定制）。
    """

    value_changed = Signal(object)

    _object_name = "heroDateInput"
    _valid_granularities = VALID_GRANULARITIES
    _default_granularity = "day"
    _include_date = True

    def __init__(
        self,
        label: str = "",
        value: DateTimeValue | None = None,
        placeholder_value: DateTimeValue | None = None,
        variant: str = "flat",
        color: str = "default",
        size: str = "md",
        radius: str | None = None,
        label_placement: str = "inside",
        granularity: str | None = None,
        hour_cycle: int | None = None,
        hide_time_zone: bool = False,
        should_force_leading_zeros: bool = True,
        min_value: DateTimeValue | None = None,
        max_value: DateTimeValue | None = None,
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
        parent: QWidget | None = None,
    ):
        """创建分段日期输入。

        Args:
            label: 标签文本。
            value: 初始值；None 为全占位。
            placeholder_value: 占位时各段增减的起点值。
            variant: flat / bordered / faded / underlined。
            color: 语义色。
            size: 尺寸档位。
            radius: 圆角档位；None 跟随尺寸默认。
            label_placement: inside / outside / outside-left / outside-top。
            granularity: day / hour / minute / second；None 用类默认值。
            hour_cycle: 12 / 24；None 跟随 locale。
            hide_time_zone: 隐藏时区段。
            should_force_leading_zeros: 数字段补前导零。
            min_value: 值域下界。
            max_value: 值域上界。
            locale: ICU locale 字符串。
            calendar: ICU 历法标识。
            is_disabled: 禁用。
            is_invalid: 外部强制错误态。
            is_required: 必填星号。
            is_readonly: 只读。
            full_width: 是否横向撑满。
            description: 描述文本。
            error_message: 错误提示文本。
            start_content: 前置自定义内容。
            end_content: 后置自定义内容。
            on_start_content_click: 前置内容点击回调。
            on_end_content_click: 后置内容点击回调。
            theme: auto / light / dark。
            parent: Qt 父对象。

        Raises:
            ValueError: granularity 不在 _valid_granularities 中时抛出。

        Note:
            越界的初始值本身也会置 invalid，不只看外部传参。
        """
        super().__init__(parent)

        granularity = granularity or self._default_granularity
        if granularity not in self._valid_granularities:
            raise ValueError(
                f"invalid granularity: {granularity!r}, expected one of {self._valid_granularities}"
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
            include_date=self._include_date,
        )
        # 越界的初始值本身就该显示为 invalid，不能只看外部传参
        self._is_invalid = is_invalid or self._state.is_invalid()

        self._segment_widgets: list[_DateSegment] = []
        self._literal_widgets: list[_SegmentLiteral] = []

        self._setup_ui()
        self._rebuild_segments()
        self._bind_events()
        self._apply_styles()
        self._update_label_animation(animate=False)

        if self._theme_mode == "auto":
            ThemeProvider.instance().register(self)
        FontProvider.instance().register(self)

    def _apply_font(self):
        """段文字宽度随字体变化，全局字体变化后重跑样式以重算最小宽度。"""
        self._apply_styles()

    # ============================================================
    # UI 结构
    # ============================================================
    def _setup_ui(self):
        """构建外框、段容器、浮动 label、helper 与 label 动画。

        Note:
            动画 parent=self，让动画随组件一起销毁，否则组件析构后
            回调访问 self._wrapper 会撞上已删除的 C++ 对象。
        """
        self.setObjectName(self._object_name)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

        # outside / outside-top 的静态 label
        self._outside_label = Text(self._label_text, weight="medium", selectable=False)
        self._outside_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._outside_label.setTextFormat(Qt.TextFormat.RichText)
        self._root.addWidget(self._outside_label, 0, Qt.AlignmentFlag.AlignLeft)

        # outside-left 的横向行
        self._outside_left_row = QWidget(self)
        _row = QHBoxLayout(self._outside_left_row)
        _row.setContentsMargins(0, 0, 0, 0)
        _row.setSpacing(8)

        self._outside_left_label = Text(self._label_text, weight="medium", selectable=False)
        self._outside_left_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._outside_left_label.setTextFormat(Qt.TextFormat.RichText)
        _row.addWidget(
            self._outside_left_label,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )

        # 背景画布（与 Input 同一个 wrapper 实现）
        self._wrapper = InputWrapper(self._outside_left_row)
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
        self._inside_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._inside_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._inside_label.raise_()

        # helper 区
        self._helper_label = Text("", weight="normal", selectable=False)
        self._helper_label.setWordWrap(True)
        self._helper_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
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
        """按当前段序重建段控件（locale / granularity 变化时调用）。

        Note:
            字面量与 timeZone 段不可编辑；重建期间关闭 updates 避免闪烁。
        """
        from ...utils import clear_layout

        self._segment_row.setUpdatesEnabled(False)
        clear_layout(self._segment_layout)
        self._segment_widgets = []
        self._literal_widgets = []

        self._add_segments(self._state, self._on_segment_edit, self._on_segment_focus_change)

        self._refresh_segment_text()
        self._segment_row.setUpdatesEnabled(True)

    def _add_literal(self, text: str):
        """在段行末尾追加一个不可编辑的字面量。

        Args:
            text: 字面量文本。
        """
        lit = _SegmentLiteral(text, parent=self._segment_row)
        self._segment_layout.addWidget(lit)
        self._literal_widgets.append(lit)

    def _add_segments(self, state: DateFieldState, on_edit, on_focus_change, field=None):
        """把状态机的段序渲染到段行末尾。

        Args:
            state: 提供段结构的状态机。
            on_edit: 段编辑回调，签名为 (seg_type, action, payload)。
            on_focus_change: 段焦点变化回调，签名为 (seg_type, focused)。
            field: 范围组件用于标记归属的标识，写入段的 field 属性；None 不写。

        Note:
            时区段只展示，不可编辑。
        """
        for spec in state.specs:
            if spec.is_literal:
                self._add_literal(spec.text)
                continue

            seg = _DateSegment(
                spec.type,
                min_digits=spec.min_digits,
                on_edit=on_edit,
                on_focus_move=self._on_segment_focus_move,
                on_focus_change=on_focus_change,
                parent=self._segment_row,
            )
            if field is not None:
                seg.field = field
            seg.set_editable(spec.is_editable and not self._is_disabled)
            seg.set_readonly(self._is_readonly)
            self._segment_layout.addWidget(seg)
            self._segment_widgets.append(seg)

    def _refresh_segment_text(self):
        """把状态机里的段值写回各段控件并调整段行尺寸。"""
        for seg in self._segment_widgets:
            seg.setText(self._state.segment_text(seg.seg_type, seg.min_digits))
        # 段宽随文本变化，重新摆放浮动 label 与最小宽度
        self._segment_row.adjustSize()

    # ============================================================
    # 事件
    # ============================================================
    def _bind_events(self):
        """给 wrapper 与 inside label 装事件过滤器并接管 wrapper 点击。"""
        self._wrapper.installEventFilter(self)
        self._wrapper.setMouseTracking(True)
        self._wrapper.mousePressEvent = self._on_wrapper_clicked
        self._inside_label.installEventFilter(self)

    def eventFilter(self, obj, event):
        """处理 wrapper hover 与 label 点击聚焦。

        Args:
            obj: 被监听对象（wrapper / inside_label）。
            event: 当前事件。

        Returns:
            label 上的鼠标按下消费并返回 True；其余交回父类。
        """
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
        """点击外框空白处：聚焦首个可编辑段。

        Args:
            event: Qt 鼠标按下事件。
        """
        self._focus_first_segment()
        QFrame.mousePressEvent(self._wrapper, event)

    def _focus_first_segment(self):
        """把焦点交给第一个可聚焦段。"""
        for seg in self._segment_widgets:
            if seg.focusPolicy() != Qt.FocusPolicy.NoFocus:
                seg.setFocus(Qt.FocusReason.MouseFocusReason)
                return

    def _editable_segments(self) -> list[_DateSegment]:
        """返回当前可聚焦的段控件列表。

        Returns:
            focusPolicy 不为 NoFocus 的 _DateSegment 列表。
        """
        return [s for s in self._segment_widgets if s.focusPolicy() != Qt.FocusPolicy.NoFocus]

    def _on_segment_focus_move(self, direction: int):
        """左右键在可编辑段之间移动焦点。

        Args:
            direction: +1 下一段、-1 上一段；越界时不移动。
        """
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
        """段获得 / 失去焦点：同步整体 focus 状态与段视觉。

        Args:
            seg_type: 发生变化的段类型。
            focused: True 表示获得焦点。

        Note:
            失焦时先 commit_segment 把中间值夹进合法范围；
            underlined 变体在整体焦点切换时展开 / 收起下划线。
        """
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
        """段控件上报的键盘动作 → 状态机 → 刷新文本 → 发信号。

        Args:
            seg_type: 段类型。
            action: increment / digit / clear / day_period。
            payload: 动作参数。

        Note:
            只读或禁用直接忽略；digit 输满后自动跳到下一段；
            只有值真的变化才发 value_changed。
        """
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
            self._state.set_segment("dayPeriod", payload)

        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation()

        after = self._state.value()
        if after != before:
            self.value_changed.emit(after)

    def _advance_focus_from(self, seg_type: str):
        """某段输满后自动跳到下一个可编辑段。

        Args:
            seg_type: 刚输满的段类型。
        """
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
        """用户是否显式设过 invalid。

        Returns:
            _user_invalid 为真时为 True，此时不再按值域自动改状态。
        """
        return getattr(self, "_user_invalid", False)

    # ============================================================
    # 公共 API
    # ============================================================
    def value(self) -> DateTimeValue | None:
        """当前值；有段未填时返回 None。

        Returns:
            完整值对象或 None。
        """
        return self._state.value()

    def set_value(self, value: DateTimeValue | None):
        """受控赋值并发 value_changed。

        Args:
            value: 新值；None 清空全部段。
        """
        self._state.set_value(value)
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()
        self._update_label_animation()
        self.value_changed.emit(self._state.value())

    def clear(self):
        """清空所有段，回到占位态并发 value_changed(None)。"""
        self._state.clear()
        self._refresh_segment_text()
        self._apply_styles()
        self._update_label_animation()
        self.value_changed.emit(None)

    def set_granularity(self, granularity: str):
        """切换时间粒度并重建段序。

        Args:
            granularity: day / hour / minute / second。

        Raises:
            ValueError: 不在 _valid_granularities 中时抛出。
        """
        if granularity not in self._valid_granularities:
            raise ValueError(f"invalid granularity: {granularity!r}")
        self._granularity = granularity
        self._recreate_state()

    def set_hour_cycle(self, hour_cycle: int | None):
        """切换 12 / 24 小时制并重建段序。

        Args:
            hour_cycle: 12 或 24；None 跟随 locale。
        """
        self._hour_cycle = hour_cycle
        self._recreate_state()

    def set_hide_time_zone(self, hide: bool):
        """切换时区段显隐并重建段序。

        Args:
            hide: True 隐藏时区段。
        """
        self._hide_time_zone = hide
        self._recreate_state()

    def set_locale(self, locale: str):
        """切换 ICU locale 并重建段序（如 en_US → de_DE 改变段顺序）。

        Args:
            locale: ICU locale 字符串。
        """
        self._locale = locale
        self._recreate_state()

    def set_calendar(self, calendar: str):
        """切换历法并重建段序。

        Args:
            calendar: ICU 历法标识。
        """
        self._calendar = calendar
        self._recreate_state()

    def set_min_value(self, value: DateTimeValue | None):
        """更新值域下界并刷新视觉。

        Args:
            value: 新下界；None 取消限制。
        """
        self._state.min_value = value
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()

    def set_max_value(self, value: DateTimeValue | None):
        """更新值域上界并刷新视觉。

        Args:
            value: 新上界；None 取消限制。
        """
        self._state.max_value = value
        self._refresh_segment_text()
        self._sync_invalid_from_state()
        self._apply_styles()

    def _recreate_state(self):
        """段序相关属性变化 → 重建状态机与段控件，保留已有值。

        Note:
            保留 placeholder、值域、前导零开关与 include_date，
            避免切换 locale / granularity 时丢失用户输入。
        """
        current = self._state.value()
        self._state = DateFieldState(
            value=current,
            placeholder_value=self._state.placeholder,
            granularity=self._granularity,
            hour_cycle=self._hour_cycle,
            locale=self._locale,
            identifier=self._calendar,
            min_value=self._state.min_value,
            max_value=self._state.max_value,
            hide_time_zone=self._hide_time_zone,
            should_force_leading_zeros=self._state.force_zeros,
            include_date=self._include_date,
        )
        self._rebuild_segments()
        self._apply_styles()

    def set_label(self, label: str):
        """更新标签文本并刷新布局与浮动动画。

        Args:
            label: 新标签；空串隐藏。
        """
        self._label_text = label
        self._apply_styles()
        self._update_label_animation()

    def set_color(self, color: str):
        """切换语义色并刷新样式。

        Args:
            color: 语义色名。
        """
        self._color = color
        self._apply_styles()

    def set_variant(self, variant: str):
        """切换外框变体并刷新样式。

        Args:
            variant: flat / bordered / faded / underlined。
        """
        self._variant = variant
        self._apply_styles()

    def set_size(self, size: str):
        """切换尺寸档位并刷新样式。

        Args:
            size: sm / md / lg。
        """
        self._size = size
        self._apply_styles()

    def set_radius(self, radius: str | None):
        """切换圆角档位并刷新样式。

        Args:
            radius: 圆角档位；None 恢复默认。
        """
        self._radius = radius
        self._apply_styles()

    def set_label_placement(self, placement: str):
        """切换 label 位置并重新摆放布局。

        Args:
            placement: inside / outside / outside-left / outside-top。
        """
        self._label_placement = placement
        self._relayout_for_label_placement()
        self._apply_styles()
        self._update_label_animation()

    def is_disabled(self) -> bool:
        """返回是否禁用。

        Returns:
            True 表示整体禁用。
        """
        return self._is_disabled

    def set_is_disabled(self, disabled: bool):
        """切换禁用态并联动各段可聚焦性。

        Args:
            disabled: True 表示禁用。
        """
        self._is_disabled = disabled
        for seg in self._segment_widgets:
            spec_editable = seg.seg_type != "timeZone"
            seg.set_editable(spec_editable and not disabled)
        self._apply_styles()

    def set_is_invalid(self, invalid: bool):
        """显式设置错误态（优先于按值域自动判定）。

        Args:
            invalid: True 表示错误态。
        """
        self._user_invalid = invalid
        self._is_invalid = invalid
        self._apply_styles()

    def set_is_required(self, required: bool):
        """切换必填星号。

        Args:
            required: True 时在 label 后加红色星号。
        """
        self._is_required = required
        self._apply_styles()

    def set_is_readonly(self, readonly: bool):
        """切换只读态并联动各段。

        Args:
            readonly: True 表示可聚焦但不可编辑。
        """
        self._is_readonly = readonly
        for seg in self._segment_widgets:
            seg.set_readonly(readonly)
        self._apply_styles()

    def set_description(self, description: str):
        """更新描述文本。

        Args:
            description: 新描述。
        """
        self._description = description
        self._apply_styles()

    def set_error_message(self, message: str):
        """更新错误提示文本。

        Args:
            message: 新错误文本。
        """
        self._error_message = message
        self._apply_styles()

    def set_start_content(self, content, on_click=None):
        """更新前置自定义内容。

        Args:
            content: 前置 widget / 图标描述。
            on_click: 可选点击回调；None 保留原回调。
        """
        self._start_content = content
        if on_click is not None:
            self._on_start_click = on_click
        self._apply_styles()

    def set_end_content(self, content, on_click=None):
        """更新后置自定义内容。

        Args:
            content: 后置 widget / 图标描述。
            on_click: 可选点击回调；None 保留原回调。
        """
        self._end_content = content
        if on_click is not None:
            self._on_end_click = on_click
        self._apply_styles()

    # ============================================================
    # 宽度接管
    # ============================================================
    def setFixedWidth(self, w: int):
        """覆写固定宽度：标记用户锁宽并重算样式。

        Args:
            w: 固定宽度（像素）。
        """
        self._user_width_locked = True
        super().setFixedWidth(w)
        self._apply_styles()

    def setMinimumWidth(self, w: int):
        """覆写最小宽度：标记用户锁宽并重算样式。

        Args:
            w: 最小宽度（像素）。
        """
        self._user_width_locked = True
        super().setMinimumWidth(w)
        self._apply_styles()

    def setMaximumWidth(self, w: int):
        """覆写最大宽度：标记用户锁宽并重算样式。

        Args:
            w: 最大宽度（像素）。
        """
        self._user_width_locked = True
        super().setMaximumWidth(w)
        self._apply_styles()

    def set_width(self, w: int):
        """便捷接口：等价 setFixedWidth。

        Args:
            w: 目标宽度（像素）。
        """
        self.setFixedWidth(w)

    # ============================================================
    # 主题
    # ============================================================
    def set_theme(self, theme: str):
        """切换主题，并维护 ThemeProvider 注册状态。

        Args:
            theme: auto / light / dark。

        Note:
            从 auto 切回固定主题时先 unregister，避免广播覆盖设定。
        """
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
        """接收 ThemeProvider 的主题变更广播。

        Args:
            theme: 变更后的主题名。

        Note:
            广播入口不重新 register/unregister，也不改 _theme_mode。
        """
        self._theme = theme
        self._apply_styles()

    @staticmethod
    def _resolve_theme(mode: str) -> str:
        """把主题模式解析成实际主题名。

        Args:
            mode: light / dark / auto。

        Returns:
            light / dark 原样返回；其余取 ThemeProvider 当前主题。
        """
        if mode in ("light", "dark"):
            return mode
        return ThemeProvider.instance().current_theme

    # ============================================================
    # 状态查询（供 Input 的 mixin 复用）
    # ============================================================
    def _has_label(self) -> bool:
        """是否有可见标签。

        Returns:
            label 文本非空时为 True。
        """
        return bool(self._label_text)

    def _has_value(self) -> bool:
        """是否已有任意段输入（供 label 浮起判断）。

        Returns:
            状态机至少有一段值时为 True。
        """
        return self._state.has_any_input()

    def _filled_within(self) -> bool:
        """label 是否浮起。

        Returns:
            恒 True——段永远渲染占位符，内容区从不为空。
        """
        return True

    def _update_label_animation(self, animate: bool = True):
        """按 placement 与 label 状态驱动浮动动画。

        Args:
            animate: 是否播放过渡；构造期传 False 直达终态。

        Note:
            仅 inside / outside 两种 placement 参与动画，且需有 label。
        """
        if self._label_placement not in ("inside", "outside"):
            return
        if not self._has_label():
            return
        self._label_anim.set_state(self._filled_within(), animate=animate)


__all__ = ["DateInput"]
