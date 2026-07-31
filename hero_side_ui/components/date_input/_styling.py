"""DateInput 的样式计算与应用 mixin（私有）。

外框（背景/边框/圆角/hover/focus）配色规则与 Input 严格同源，直接复用
Input 的 `_resolve_wrapper_colors` 系列决策，保证两个组件视觉不漂移。
本文件只额外负责 DateInput 特有的"段"四态配色：
editable / placeholder / invalid / focus。
"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLayout, QSizePolicy, QWidget

from ...themes import DATE_INPUT_SIZES, HEROUI_COLORS, RADIUS
from ..input._styling import _InputStylingMixin


class _DateInputStylingMixin(_InputStylingMixin):
    """DateInput 的样式 mixin。

    继承 Input 的颜色决策方法（_flat_bg_colors / _resolve_wrapper_colors /
    _resolve_label_*_color），但完全重写 _apply_styles —— DateInput 内部是
    段列表而非 QLineEdit，布局与文本应用路径不同。
    """

    def _size_config(self) -> dict:
        return DATE_INPUT_SIZES.get(self._size, DATE_INPUT_SIZES["md"])

    def _apply_styles(self):
        """计算并应用全部样式。"""
        is_dark = self._theme == "dark"
        size_config = self._size_config()
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["default"])
        dc = HEROUI_COLORS["default"]

        # ---- 根控件尺寸策略 ----
        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._wrapper.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        else:
            # wrapper 默认 Expanding 会撑满 root，root 自己的 policy 拦不住，
            # 必须两处同时收紧才能真正紧凑显示。
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            self._wrapper.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )

        # ---- 高度 ----
        is_inside = self._label_placement == "inside" and self._has_label()
        is_outside_float = self._label_placement == "outside" and self._has_label()
        height = size_config["inside_height"] if is_inside else size_config["height"]
        self._wrapper.setFixedHeight(height)

        # ---- 最小宽度 ----
        if not getattr(self, "_user_width_locked", False):
            min_w = self._natural_min_width(size_config)
            QWidget.setMinimumWidth(self, min_w)
            QWidget.setMinimumWidth(self._wrapper, min_w)
        else:
            QWidget.setMinimumWidth(self._wrapper, 0)
            wrap_layout = self._wrapper.layout()
            if wrap_layout is not None:
                wrap_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        # ---- outside 浮动 label 的顶部预留 ----
        if is_outside_float:
            self._root.setContentsMargins(
                0, size_config["label_float_font_size"] + 6, 0, 0
            )
        else:
            self._root.setContentsMargins(0, 0, 0, 0)

        # ---- wrapper padding ----
        pad_x = size_config["padding_x"]
        pad_y = (
            size_config["padding_y"] if not is_inside else size_config["inside_padding_y"]
        )
        if self._radius == "full":
            pad_x += 4
        if self._variant == "underlined":
            self._wrapper.layout().setContentsMargins(4, 0, 4, 0)
        else:
            self._wrapper.layout().setContentsMargins(pad_x, pad_y, pad_x, pad_y)

        # ---- inside 模式下段行下移，给浮起的 label 让位 ----
        if is_inside:
            top_space = size_config["inside_input_top_space"]
            self._inner_layout.setContentsMargins(0, top_space, 0, 0)
            self._start_slot_layout.setContentsMargins(0, top_space, 0, 0)
            self._end_slot_layout.setContentsMargins(0, top_space, 0, 0)
        else:
            self._inner_layout.setContentsMargins(0, 0, 0, 0)
            self._start_slot_layout.setContentsMargins(0, 0, 0, 0)
            self._end_slot_layout.setContentsMargins(0, 0, 0, 0)

        # ---- 外框背景/边框（复用 Input 的颜色决策）----
        self._apply_wrapper_paint(is_dark, colors, dc, size_config)

        # ---- 段配色 ----
        self._apply_segment_styles(is_dark, colors, dc, size_config)

        # ---- 禁用态 ----
        if self._is_disabled:
            self._wrapper.setEnabled(False)
            op = QGraphicsOpacityEffect(self)
            op.setOpacity(0.5)
            self.setGraphicsEffect(op)
        else:
            self._wrapper.setEnabled(True)
            self.setGraphicsEffect(None)

        # ---- label 配色 ----
        self._label_color_resting = QColor(
            self._resolve_label_resting_color(is_dark, colors, dc)
        )
        self._label_color_floated = QColor(
            self._resolve_label_floated_color(is_dark, colors, dc)
        )

        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"
        display_label = self._label_text + req_mark if self._label_text else ""
        for lbl in (self._outside_label, self._outside_left_label):
            lbl.setText(display_label)
            lbl.set_size(size_config["outside_label_font_size"])
            lbl.set_color(self._label_color_floated.name())
        self._inside_label.set_size(size_config["label_font_size"])

        # ---- start / end content ----
        self._render_adornment_icons(is_dark, colors, dc, size_config)

        # ---- helper ----
        self._apply_helper_styles(is_dark, dc, size_config)

        # ---- 重新摆放 ----
        self._relayout_for_label_placement()
        self._reposition_inside_label()
        self._reposition_underline()

    def _qcolor(self, s) -> QColor:
        """把 hex / "rgba(r,g,b,a)" / transparent / QColor 统一转成 QColor。

        必须自己解析 rgba 字符串：Qt 的 QColor 不认 "rgba(...)"，直接构造会
        得到 invalid QColor，取 .name() 或用于填充都会变纯黑。
        """
        if isinstance(s, QColor):
            return QColor(s)
        if not s or s == "transparent":
            return QColor(0, 0, 0, 0)
        s = s.strip()
        if s.startswith("rgba"):
            inner = s[s.index("(") + 1 : s.rindex(")")]
            parts = [p.strip() for p in inner.split(",")]
            a = int(float(parts[3]) * 255) if len(parts) == 4 else 255
            return QColor(
                int(float(parts[0])), int(float(parts[1])), int(float(parts[2])), a
            )
        c = QColor(s)
        return c if c.isValid() else QColor(0, 0, 0, 0)

    # ------------------------------------------------------------
    # 外框绘制
    # ------------------------------------------------------------
    def _apply_wrapper_paint(self, is_dark, colors, dc, size_config):
        """把 variant 对应的背景/边框/下划线交给 _InputWrapper 画。"""
        (
            bg,
            border,
            border_color,
            bg_hover,
            bg_focus,
            border_hover,
            border_focus,
            main_color,
        ) = self._resolve_wrapper_colors(is_dark, colors, dc)

        if self._is_focused:
            cur_bg, cur_border = bg_focus, border_focus
        elif self._is_hover:
            cur_bg, cur_border = bg_hover, border_hover
        else:
            cur_bg, cur_border = bg, border_color

        try:
            radius_px = int(self._resolve_radius(size_config).replace("px", ""))
        except ValueError:
            radius_px = 8

        bw = size_config["border_width"]
        animate = getattr(self, "_styles_applied_once", False)

        if self._variant == "underlined":
            base_line = dc[700] if is_dark else dc[200]
            hover_line = dc[600] if is_dark else dc[300]
            self._wrapper.set_static(border_width=0, radius_px=0, show_bottom_line=True)
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(
                self._qcolor(hover_line if self._is_hover else base_line),
                animate=animate,
            )
            self._underline.set_color(QColor(main_color))
            self._underline.show()
        elif self._variant == "flat":
            self._wrapper.set_static(
                border_width=0, radius_px=radius_px, show_bottom_line=False
            )
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()
        elif self._variant == "faded":
            self._wrapper.set_static(
                border_width=bw, radius_px=radius_px, show_bottom_line=False
            )
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()
        else:  # bordered
            self._wrapper.set_static(
                border_width=bw, radius_px=radius_px, show_bottom_line=False
            )
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        self._styles_applied_once = True

    # ------------------------------------------------------------
    # 段配色
    # ------------------------------------------------------------
    def _apply_segment_styles(self, is_dark, colors, dc, size_config):
        """逐段套用字色/焦点底色/字体。

        HeroUI 段四态（date-input.ts 的 segment slot）：
          - 已填写(editable 非 placeholder)：主文字色
          - 占位(placeholder)：更淡一档
          - invalid：danger 系
          - focus：底色 {color}-400 半透明 + 字色转主色
        """
        from ...core import make_text_qfont

        font = make_text_qfont(size_config["input_font_size"], "normal")
        filled_color, placeholder_color = self._resolve_segment_text_colors(
            is_dark, colors, dc
        )
        focus_bg = self._resolve_segment_focus_bg(is_dark, colors, dc)
        focus_text = self._resolve_segment_focus_text(is_dark, colors, dc)
        radius_px = size_config["segment_radius"]
        padding_x = size_config["segment_padding_x"]

        for seg in self._segment_widgets:
            seg.setFont(font)
            focused = seg.hasFocus()
            if seg.seg_type == "timeZone":
                # 时区是只读元信息，恒定用弱化色，不参与聚焦态
                color = placeholder_color
            elif focused:
                color = focus_text
            elif self._state.is_placeholder(seg.seg_type):
                color = placeholder_color
            else:
                color = filled_color
            seg.apply_visual(
                text_color=color,
                focus_bg=focus_bg,
                radius_px=radius_px,
                padding_x=padding_x,
                focused=focused,
            )

        for lit in self._literal_widgets:
            lit.setFont(font)
            # 分隔符在 HeroUI 里也走 segment slot，但没有 data-editable，
            # 因此恒定取 text-foreground-500（弱化色），不随填写状态变亮。
            lit.apply_visual(text_color=placeholder_color)

    def _resolve_segment_text_colors(self, is_dark, colors, dc):
        """返回 (已填写段字色, 占位段字色)，均为 QColor。"""
        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            return QColor(d[500]), QColor(d[300] if not is_dark else d[400])

        if self._color != "default":
            if self._color in ("success", "warning"):
                filled = colors[500] if is_dark else colors[600]
            elif self._color == "danger":
                filled = colors[500]
            else:
                filled = colors[400] if is_dark else colors[500]
            return QColor(filled), QColor(colors[300] if not is_dark else colors[600])

        return (
            QColor(dc[100] if is_dark else dc[900]),
            QColor(dc[500] if is_dark else dc[400]),
        )

    def _resolve_segment_focus_bg(self, is_dark, colors, dc):
        """段聚焦底色：{color}-400 半透明（暗色更淡，对齐 dark: /20）。

        必须 QColor(hex) + setAlphaF 构造，不能把 rgba() 字符串喂 QColor。
        """
        alpha = 0.20 if is_dark else 0.50
        if self._is_invalid:
            base = HEROUI_COLORS["danger"][400]
        elif self._color == "default":
            base = dc[400]
        else:
            base = colors[400]
        c = QColor(base)
        c.setAlphaF(alpha)
        return c

    def _resolve_segment_focus_text(self, is_dark, colors, dc):
        """段聚焦字色：default 走前景反色，其余走主色。"""
        if self._is_invalid:
            return QColor(HEROUI_COLORS["danger"][500])
        if self._color == "default":
            return QColor(dc[50] if is_dark else dc[900])
        if self._color in ("success", "warning"):
            return QColor(colors[500] if is_dark else colors[600])
        return QColor(colors[400] if is_dark else colors[500])

    # ------------------------------------------------------------
    # helper 区
    # ------------------------------------------------------------
    def _apply_helper_styles(self, is_dark, dc, size_config):
        helper_font = size_config["helper_font_size"]
        if self._is_invalid and self._error_message:
            self._helper_label.setText(self._error_message)
            self._helper_label.set_size(helper_font)
            self._helper_label.set_color(HEROUI_COLORS["danger"][500])
            self._helper_label.show()
        elif self._description:
            self._helper_label.setText(self._description)
            self._helper_label.set_size(helper_font)
            self._helper_label.set_color(dc[400] if is_dark else dc[500])
            self._helper_label.show()
        else:
            self._helper_label.hide()

    # ------------------------------------------------------------
    # 尺寸
    # ------------------------------------------------------------
    def _natural_min_width(self, size_config) -> int:
        """按段文本实际宽度估算最小宽度。

        DateInput 内容宽度是确定的（段数固定），不像 Input 需要给用户留
        输入空间，因此不沿用 INPUT_SIZES 的 240/260/300，改为实测撑开，
        避免 granularity=second 时段被挤掉。
        """
        content = self._inner.sizeHint().width()
        pad = size_config["padding_x"] * 2
        extras = 0
        if self._start_slot.isVisible():
            extras += self._start_slot.sizeHint().width() + size_config["gap"]
        if self._end_slot.isVisible():
            extras += self._end_slot.sizeHint().width() + size_config["gap"]
        return max(120, content + pad + extras)

    def _resolve_radius(self, size_config: dict) -> str:
        radius_key = self._radius or size_config.get("default_radius", "md")
        if radius_key == "full":
            is_inside = self._label_placement == "inside" and self._has_label()
            h = size_config["inside_height"] if is_inside else size_config["height"]
            return f"{h // 2}px"
        return RADIUS.get(radius_key, RADIUS["md"])


__all__ = ["_DateInputStylingMixin"]
