"""DateInput 样式 mixin：外框复用 Input 决策，额外负责段四态配色。"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLayout, QSizePolicy, QWidget

from ..._shared.fields import InputStylingMixin
from ...themes import DATE_INPUT_SIZES, HEROUI_COLORS, RADIUS


class _DateInputStylingMixin(InputStylingMixin):
    """DateInput 的样式 mixin。

    继承 Input 颜色决策方法，但重写 _apply_styles——内部是段列表而非
    QLineEdit。
    """

    def _size_config(self) -> dict:
        """取当前尺寸档位配置。

        Returns:
            DATE_INPUT_SIZES 中的配置字典；非法档位回退 md。
        """
        return DATE_INPUT_SIZES.get(self._size, DATE_INPUT_SIZES["md"])

    def _apply_styles(self):
        """计算并应用全部样式：尺寸、布局、外框、段配色、label、helper。

        Note:
            非 full_width 时 root 与 wrapper 的 sizePolicy 必须同时收紧，
            否则 wrapper 默认 Expanding 会撑满 root；用户锁过宽度时
            不再写 minWidth，并解除 wrapper 布局的 sizeConstraint。
        """
        is_dark = self._theme == "dark"
        size_config = self._size_config()
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["default"])
        dc = HEROUI_COLORS["default"]

        # ---- 根控件尺寸策略 ----
        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._wrapper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        else:
            # wrapper 默认 Expanding 会撑满 root，root 自己的 policy 拦不住，
            # 必须两处同时收紧才能真正紧凑显示。
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            self._wrapper.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

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
            self._root.setContentsMargins(0, size_config["label_float_font_size"] + 6, 0, 0)
        else:
            self._root.setContentsMargins(0, 0, 0, 0)

        # ---- wrapper padding ----
        pad_x = size_config["padding_x"]
        pad_y = size_config["padding_y"] if not is_inside else size_config["inside_padding_y"]
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
        self._label_color_resting = QColor(self._resolve_label_resting_color(is_dark, colors, dc))
        self._label_color_floated = QColor(self._resolve_label_floated_color(is_dark, colors, dc))

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
        """把 hex / rgba / transparent / QColor 统一转 QColor。

        Args:
            s: 颜色字符串或 QColor 实例。

        Returns:
            对应 QColor；非法值返回全透明黑。

        Note:
            Qt QColor 不认 "rgba(...)" 字符串，必须自行解析。
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
            return QColor(int(float(parts[0])), int(float(parts[1])), int(float(parts[2])), a)
        c = QColor(s)
        return c if c.isValid() else QColor(0, 0, 0, 0)

    # ------------------------------------------------------------
    # 外框绘制
    # ------------------------------------------------------------
    def _apply_wrapper_paint(self, is_dark, colors, dc, size_config):
        """把 variant 对应的背景 / 边框 / 下划线交给 InputWrapper 画。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。
            size_config: 尺寸 token。

        Note:
            焦点优先于 hover 选色；首次应用不走颜色补间（animate=False），
            之后由 _styles_applied_once 标记开启过渡。
        """
        (
            bg,
            _border,
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
            self._wrapper.set_static(border_width=0, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()
        elif self._variant == "faded":
            self._wrapper.set_static(border_width=bw, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()
        else:  # bordered
            self._wrapper.set_static(border_width=bw, radius_px=radius_px, show_bottom_line=False)
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
            self._underline.hide()

        self._styles_applied_once = True

    # ------------------------------------------------------------
    # 段配色
    # ------------------------------------------------------------
    def _apply_segment_styles(self, is_dark, colors, dc, size_config):
        """逐段套用字色 / 焦点底色 / 字体（editable/placeholder/invalid/focus 四态）。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。
            size_config: 尺寸 token。

        Note:
            timeZone 是只读元信息恒用弱化色；字面量分隔符也恒定取
            foreground-500 弱化色，不随填写状态变亮。
        """
        font_size = size_config["input_font_size"]
        filled_color, placeholder_color = self._resolve_segment_text_colors(is_dark, colors, dc)
        focus_bg = self._resolve_segment_focus_bg(is_dark, colors, dc)
        focus_text = self._resolve_segment_focus_text(is_dark, colors, dc)
        radius_px = size_config["segment_radius"]
        padding_x = size_config["segment_padding_x"]

        for seg in self._segment_widgets:
            seg.set_size(font_size)
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
            lit.set_size(font_size)
            # 分隔符在 HeroUI 里也走 segment slot，但没有 data-editable，
            # 因此恒定取 text-foreground-500（弱化色），不随填写状态变亮。
            lit.apply_visual(text_color=placeholder_color)

    def _resolve_segment_text_colors(self, is_dark, colors, dc):
        """返回 (已填写段字色, 占位段字色)。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。

        Returns:
            两个 QColor；invalid 态走 danger 色，其余按语义色 / default 取值。
        """
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

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。

        Returns:
            已设 alphaF 的 QColor。

        Note:
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
        """段聚焦字色：default 走前景反色，其余走主色。

        Args:
            is_dark: 是否深色主题。
            colors: 当前语义色阶字典。
            dc: default 色阶字典。

        Returns:
            焦点段应使用的 QColor；invalid 态走 danger-500。
        """
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
        """刷新 helper 文本：invalid 错误优先，其次描述，否则隐藏。

        Args:
            is_dark: 是否深色主题。
            dc: default 色阶字典。
            size_config: 尺寸 token（取 helper_font_size）。
        """
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
        """按段文本实测估算最小宽度，不用 INPUT_SIZES 的固定下限。

        Args:
            size_config: 尺寸 token（padding_x / gap）。

        Returns:
            至少 120px 的估算宽度 = 内容 sizeHint + padding + 可见插槽宽度。
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
        """解析外框圆角值。

        Args:
            size_config: 尺寸 token（default_radius / height / inside_height）。

        Returns:
            full 按当前高度折算；其余取全局 RADIUS token。
        """
        radius_key = self._radius or size_config.get("default_radius", "md")
        if radius_key == "full":
            is_inside = self._label_placement == "inside" and self._has_label()
            h = size_config["inside_height"] if is_inside else size_config["height"]
            return f"{h // 2}px"
        return RADIUS.get(radius_key, RADIUS["md"])


__all__ = ["_DateInputStylingMixin"]
