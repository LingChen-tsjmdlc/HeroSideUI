"""Textarea 组件的样式计算与应用 mixin（私有）。

把 _apply_styles 及其辅助颜色/几何刷新方法（约 500 行）从主组件抽出。
包括："应用 styles 后做对应的几何重排"（label_placement / inside-label
位置浮动）也归到此 mixin，因为它们是 styling 的延伸。
"""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton

from typing import Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPalette
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QSizePolicy, QWidget

from ...themes import HEROUI_COLORS, RADIUS, TEXTAREA_SIZES
from ...utils import hex_to_rgba, load_svg_icon


class _TextareaStylingMixin:
    """Textarea 样式 mixin。"""

    # ============================================================
    # 样式应用
    # ============================================================
    def _apply_styles(self):
        is_dark = self._theme == "dark"
        size_config = TEXTAREA_SIZES.get(self._size, TEXTAREA_SIZES["md"])
        colors = HEROUI_COLORS.get(self._color, HEROUI_COLORS["default"])
        dc = HEROUI_COLORS["default"]

        # ---- 提前给 QTextEdit 直接 setFont，让 fontMetrics.lineSpacing()
        #      在 row_h 计算之前就拿到正确字号；后面走 Text/FontProvider 同源的字体
        #      也使用同一个字号，不会冲突。
        from ...core import make_text_qfont

        font_for_metrics = make_text_qfont(size_config["input_font_size"], "normal")
        self.text_edit.setFont(font_for_metrics)

        if self._full_width:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        if self._is_disabled:
            self.setStyleSheet("QWidget#heroTextarea { color: palette(disabled); }")
        else:
            self.setStyleSheet("")

        # ---- 最小宽度 ----
        min_w = size_config.get("min_width", 260)
        self.setMinimumWidth(min_w)
        self._wrapper.setMinimumWidth(min_w)

        is_inside = self._label_placement == "inside" and self._has_label()
        is_outside_float = self._label_placement == "outside" and self._has_label()

        # ---- 根容器上边距 (outside 模式给浮起 label 留位置) ----
        if is_outside_float:
            top_reserve = size_config["label_float_font_size"] + 6
            self._root.setContentsMargins(0, top_reserve, 0, 0)
        else:
            self._root.setContentsMargins(0, 0, 0, 0)

        # ---- inputWrapper padding ----
        pad_x = size_config["padding_x"]
        pad_y = (
            size_config["padding_y"]
            if not is_inside
            else size_config["inside_padding_y"]
        )
        if self._radius == "full":
            pad_x += 4
        self._wrapper.layout().setContentsMargins(pad_x, pad_y, pad_x, pad_y)

        # ---- innerWrapper / top_right_slot / clear_btn top margin ----
        # 三槽新设计：
        #   top_right_slot: 在 layout 内，AlignTop；inside 模式下要下推 inside_input_top_space
        #     以避开浮起的 label（否则 label 和 top_right_content 会重叠）
        #   center_right / bottom_right: 绝对定位，resizeEvent 里实时摆放，不受 layout 影响
        #   clear_btn: 行为同 top_right_slot
        if is_inside:
            top_space = size_config["inside_input_top_space"]
            self._inner_layout.setContentsMargins(0, top_space, 0, 0)
            self._top_right_slot_layout.setContentsMargins(0, top_space, 0, 0)
            self._clear_btn.setContentsMargins(0, top_space, 0, 0)
        else:
            self._inner_layout.setContentsMargins(0, 0, 0, 0)
            self._top_right_slot_layout.setContentsMargins(0, 0, 0, 0)
            self._clear_btn.setContentsMargins(0, 0, 0, 0)

        # ---- inputWrapper 颜色（复用 Input 的颜色决策逻辑）----
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
            cur_bg = bg_focus
            cur_border = border_focus
        elif self._is_hover:
            cur_bg = bg_hover
            cur_border = border_hover
        else:
            cur_bg = bg
            cur_border = border_color

        radius_px_str = self._resolve_radius(size_config)
        try:
            radius_px = int(radius_px_str.replace("px", ""))
        except Exception:
            radius_px = 8

        bw = size_config["border_width"]
        animate = getattr(self, "_styles_applied_once", False)

        if self._variant == "flat":
            self._wrapper.set_static(
                border_width=0, radius_px=radius_px, show_bottom_line=False
            )
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
        elif self._variant == "faded":
            self._wrapper.set_static(
                border_width=bw, radius_px=radius_px, show_bottom_line=False
            )
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
        elif self._variant == "bordered":
            self._wrapper.set_static(
                border_width=bw, radius_px=radius_px, show_bottom_line=False
            )
            self._wrapper.set_bg_color(QColor(0, 0, 0, 0), animate=False)
            self._wrapper.set_border_color(self._qcolor(cur_border), animate=animate)
            self._wrapper.set_bottom_line_color(QColor(0, 0, 0, 0), animate=False)
        else:
            # fallback to flat
            self._wrapper.set_static(
                border_width=0, radius_px=radius_px, show_bottom_line=False
            )
            self._wrapper.set_bg_color(self._qcolor(cur_bg), animate=animate)
            self._wrapper.set_border_color(QColor(0, 0, 0, 0), animate=False)

        self._styles_applied_once = True

        # ---- text_edit 样式 ----
        fg_color, placeholder_color = self._resolve_input_text_color(
            is_dark, colors, dc
        )
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {fg_color};
                font-size: {size_config['input_font_size']}px;
                selection-background-color: {colors[200]};
                padding: 0;
            }}
            """)
        # 字体不走 QSS，走 Text/FontProvider 同源：
        from ...core import make_text_qfont

        self.text_edit.setFont(
            make_text_qfont(size_config["input_font_size"], "normal")
        )
        # 注：QScrollBar 样式由 ScrollStyle 单例统一管理（apply_global），
        # 这里不再写局部 QSS。如果需要某个 textarea 用不同色滚动条，
        # 可以自己 text_edit.setStyleSheet 追加 QScrollBar 段。
        pal = self.text_edit.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(placeholder_color))
        pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.text_edit.setPalette(pal)
        # viewport 同步
        vp = self.text_edit.viewport()
        vp_pal = vp.palette()
        vp_pal.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        vp.setPalette(vp_pal)

        # ---- 禁用态 ----
        if self._is_disabled:
            self.text_edit.setEnabled(False)
            self._wrapper.setEnabled(False)
            op = QGraphicsOpacityEffect(self)
            op.setOpacity(0.5)
            self.setGraphicsEffect(op)
        else:
            self.text_edit.setEnabled(True)
            self._wrapper.setEnabled(True)
            self.setGraphicsEffect(None)

        # ---- Label 颜色 ----
        self._label_color_resting = QColor(
            self._resolve_label_resting_color(is_dark, colors, dc)
        )
        self._label_color_floated = QColor(
            self._resolve_label_floated_color(is_dark, colors, dc)
        )

        # ---- outside label ----
        outside_label_font = size_config["outside_label_font_size"]
        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"
        display_label = self._label_text + req_mark if self._label_text else ""
        for lbl in (self._outside_label, self._outside_left_label):
            lbl.setText(display_label)
            lbl.set_size(outside_label_font)
            lbl.set_color(self._label_color_floated.name())

        # ---- 内部 label 字号 ----
        # 颜色由动画插值后用 RichText <span> 写入；这里只调字号。
        self._inside_label.set_size(size_config["label_font_size"])

        # ---- start/end icon ----
        self._render_adornment_icons(is_dark, colors, dc, size_config)

        # ---- clear button icon ----
        if self._is_clearable:
            ic_size = size_config["clear_icon_size"]
            ic_color = QColor(dc[400] if is_dark else dc[500])
            pix = load_svg_icon(
                "heroicons--x-circle-solid", size=ic_size, color=ic_color
            )
            self._clear_btn.setIcon(pix)
            self._clear_btn.setIconSize(QSize(ic_size, ic_size))
            self._clear_btn.setFixedSize(ic_size + 4, ic_size + 4)
            self._clear_btn.setVisible(True)
        else:
            self._clear_btn.hide()

        # ---- helper ----
        helper_font = size_config["helper_font_size"]
        if self._is_invalid and self._error_message:
            self._helper_label.setText(self._error_message)
            self._helper_label.set_size(helper_font)
            self._helper_label.set_color(HEROUI_COLORS["danger"][500])
            self._helper_label.show()
        elif self._description:
            self._helper_label.setText(self._description)
            desc_color = dc[400] if is_dark else dc[500]
            self._helper_label.set_size(helper_font)
            self._helper_label.set_color(desc_color)
            self._helper_label.show()
        else:
            self._helper_label.hide()

        # ---- 重新摆 label/高度 ----
        self._relayout_for_label_placement()
        self._update_textarea_height()

        # ---- 把自己的滚动条颜色注册给 ScrollStyle，让 hover 动画也用这个色 ----
        # 仅当组件 color 不是 "default" 时才注册自定义色；否则让全局 ScrollStyle 默认色
        # （neutral —— 纯灰中性色）生效。这样 Textarea(color="primary") 滚动条用 primary，
        # Textarea(color="default") 滚动条用 neutral（更纯灰、更中性）。
        try:
            from ...core import ScrollStyle

            v_bar = self.text_edit.verticalScrollBar()
            h_bar = self.text_edit.horizontalScrollBar()
            override = self._color if self._color != "default" else None
            ScrollStyle.instance().set_bar_color(v_bar, override)
            ScrollStyle.instance().set_bar_color(h_bar, override)
        except Exception:
            pass  # 没装 ScrollStyle 也不影响 textarea 工作

        # ---- grip 颜色跟随主题（亮色 neutral-400，暗色 neutral-500）----
        if hasattr(self, "_resize_grip"):
            grip_color = (
                HEROUI_COLORS["neutral"][500]
                if is_dark
                else HEROUI_COLORS["neutral"][400]
            )
            self._resize_grip.set_line_color(QColor(grip_color))

    # ------------------------------------------------------------
    # 颜色决策（与 Input 完全对齐，复制实现）
    # ------------------------------------------------------------
    def _flat_bg_colors(self, is_dark: bool, colors: dict, dc: dict):
        is_default = self._color == "default"
        if is_default:
            if is_dark:
                bg = dc[800]
                bg_hover = dc[700]
                bg_focus = dc[700]
            else:
                bg = dc[100]
                bg_hover = dc[200]
                bg_focus = dc[200]
        else:
            if is_dark:
                bg = hex_to_rgba(colors[500], 0.15)
                bg_hover = hex_to_rgba(colors[500], 0.25)
                bg_focus = hex_to_rgba(colors[500], 0.25)
            else:
                bg = colors[100]
                bg_hover = colors[200]
                bg_focus = colors[200]
        return bg, bg_hover, bg_focus

    def _resolve_wrapper_colors(self, is_dark: bool, colors: dict, dc: dict):
        is_default = self._color == "default"
        main_color = colors[500] if not is_default else (dc[50] if is_dark else dc[900])

        if self._variant == "flat":
            bg, bg_hover, bg_focus = self._flat_bg_colors(is_dark, colors, dc)
            border = "transparent"
            border_color = "transparent"
            border_hover = "transparent"
            border_focus = "transparent"

        elif self._variant == "faded":
            bg, bg_hover, bg_focus = self._flat_bg_colors(is_dark, colors, dc)
            if is_default:
                default_border = dc[700] if is_dark else dc[200]
            else:
                default_border = colors[700] if is_dark else colors[200]
            default_border_hover = dc[500] if is_dark else dc[400]
            border = default_border
            border_color = default_border
            if is_default:
                border_hover = default_border_hover
                border_focus = default_border_hover
            else:
                border_hover = colors[500]
                border_focus = colors[500]

        elif self._variant == "bordered":
            flat_bg, _, _ = self._flat_bg_colors(is_dark, colors, dc)
            bg = "transparent"
            bg_hover = "transparent"
            bg_focus = "transparent"
            border = flat_bg
            border_color = flat_bg
            if is_default:
                border_hover = dc[400]
                border_focus = dc[500]
            else:
                if is_dark:
                    border_hover = colors[600]
                    border_focus = colors[500]
                else:
                    border_hover = colors[400]
                    border_focus = colors[500]
        else:
            bg = "transparent"
            bg_hover = "transparent"
            bg_focus = "transparent"
            border = "transparent"
            border_color = "transparent"
            border_hover = "transparent"
            border_focus = "transparent"

        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            main_color = d[500]
            if self._variant == "flat":
                bg = hex_to_rgba(d[500], 0.15) if is_dark else d[50]
                bg_hover = hex_to_rgba(d[500], 0.25) if is_dark else d[100]
                bg_focus = hex_to_rgba(d[500], 0.15) if is_dark else d[50]
            elif self._variant == "bordered":
                border = d[500]
                border_color = d[500]
                border_hover = d[500]
                border_focus = d[500]
            elif self._variant == "faded":
                border = d[500]
                border_color = d[500]
                border_hover = d[500]
                border_focus = d[500]

        return (
            bg,
            border,
            border_color,
            bg_hover,
            bg_focus,
            border_hover,
            border_focus,
            main_color,
        )

    def _resolve_input_text_color(self, is_dark: bool, colors: dict, dc: dict):
        if self._is_invalid:
            d = HEROUI_COLORS["danger"]
            return (
                d[400] if is_dark else d[500],
                d[400] if is_dark else d[500],
            )
        if self._variant == "flat" and self._color != "default":
            if self._color in ("success", "warning"):
                fg = colors[500] if is_dark else colors[600]
                ph = colors[500] if is_dark else colors[600]
            elif self._color == "danger":
                fg = colors[500] if is_dark else colors[500]
                ph = colors[500] if is_dark else colors[500]
            else:
                fg = colors[400] if is_dark else colors[500]
                ph = colors[400] if is_dark else colors[500]
            return fg, ph
        fg = dc[100] if is_dark else dc[900]
        ph = dc[400] if is_dark else dc[500]
        return fg, ph

    def _resolve_label_resting_color(self, is_dark, colors, dc) -> str:
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        return dc[400] if is_dark else dc[500]

    def _resolve_label_floated_color(self, is_dark, colors, dc) -> str:
        if self._is_invalid:
            return HEROUI_COLORS["danger"][500]
        if self._color != "default":
            if self._variant == "flat" and self._color in ("success", "warning"):
                return colors[500] if is_dark else colors[600]
            return colors[500] if not is_dark else colors[400]
        return dc[100] if is_dark else dc[900]

    def _resolve_radius(self, size_config: dict) -> str:
        radius_key = self._radius or size_config.get("default_radius", "md")
        if radius_key == "full":
            # textarea 高度可变，full 用一个稳定的大圆角而不是 height/2
            return "20px"
        return RADIUS.get(radius_key, RADIUS["md"])

    # ------------------------------------------------------------
    # start / end content
    # ------------------------------------------------------------
    def _render_adornment_icons(self, is_dark, colors, dc, size_config):
        # top_right_slot: 在 layout 内（layout 已管好位置）
        self._fill_slot(
            slot=self._top_right_slot,
            slot_layout=self._top_right_slot_layout,
            content=self._top_right_content,
            on_click=self._on_top_right_click,
            icon_size=size_config["end_icon_size"],
            is_dark=is_dark,
            dc=dc,
        )
        # center_right / bottom_right：绝对定位 holder
        self._fill_slot(
            slot=self._center_right_holder,
            slot_layout=self._center_right_slot_layout,
            content=self._center_right_content,
            on_click=self._on_center_right_click,
            icon_size=size_config["end_icon_size"],
            is_dark=is_dark,
            dc=dc,
        )
        self._fill_slot(
            slot=self._bottom_right_holder,
            slot_layout=self._bottom_right_slot_layout,
            content=self._bottom_right_content,
            on_click=self._on_bottom_right_click,
            icon_size=size_config["end_icon_size"],
            is_dark=is_dark,
            dc=dc,
        )
        # 绝对定位的 holder 渲染完后，sizeHint 可能变了，重摆位置
        self._reposition_absolute_holders()

    def _fill_slot(self, slot, slot_layout, content, on_click, icon_size, is_dark, dc):
        while slot_layout.count():
            item = slot_layout.takeAt(0)
            w = item.widget()
            if w is None:
                continue
            if w.property("_hs_internal") is True:
                w.deleteLater()
            else:
                w.setParent(None)

        if content is None:
            slot.hide()
            return

        if isinstance(content, QWidget):
            slot_layout.addWidget(content, 0, Qt.AlignmentFlag.AlignVCenter)
            content.show()
            slot.show()
            return

        icon_color = QColor(dc[400] if is_dark else dc[500])
        pix = load_svg_icon(str(content), size=icon_size, color=icon_color)

        if on_click is not None:
            btn = QPushButton()
            btn.setProperty("_hs_internal", True)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(pix)
            btn.setIconSize(QSize(icon_size, icon_size))
            btn.setFixedSize(icon_size + 4, icon_size + 4)
            btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; padding: 0; }"
            )
            btn.clicked.connect(on_click)
            slot_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            lbl = QLabel()
            lbl.setProperty("_hs_internal", True)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lbl.setFixedSize(icon_size, icon_size)
            lbl.setPixmap(pix)
            slot_layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        slot.show()

    # ------------------------------------------------------------
    # label 位置 & 浮动定位
    # ------------------------------------------------------------
    def _relayout_for_label_placement(self):
        has_label = self._has_label()
        self._outside_label.setVisible(False)
        self._outside_left_label.setVisible(False)
        self._inside_label.setVisible(False)
        self._outside_left_row.setContentsMargins(0, 0, 0, 0)

        if self._label_placement == "outside-top" and has_label:
            self._outside_label.setVisible(True)
        elif self._label_placement == "outside-left" and has_label:
            self._outside_left_label.setVisible(True)
        elif self._label_placement in ("inside", "outside") and has_label:
            self._inside_label.setVisible(True)

    def _reposition_inside_label(self):
        if not self._has_label() or self._label_placement not in ("inside", "outside"):
            return
        progress = self._label_anim._progress
        self._apply_label_progress(progress)

    def _apply_label_progress(self, progress: float):
        size_config = TEXTAREA_SIZES.get(self._size, TEXTAREA_SIZES["md"])
        f_rest = size_config["label_font_size"]
        f_float = size_config["label_float_font_size"]
        font_size = f_rest + (f_float - f_rest) * progress

        from ...core import make_text_qfont

        weight = "medium" if progress > 0.5 else "normal"
        font = make_text_qfont(int(round(font_size)), weight)
        self._inside_label.setFont(font)
        self._inside_label.adjustSize()

        from PySide6.QtCore import QPoint

        wrapper_pos_in_self = self._wrapper.mapTo(self, QPoint(0, 0))
        wrapper_x = wrapper_pos_in_self.x()
        wrapper_y = wrapper_pos_in_self.y()
        wrapper_h = self._wrapper.height()

        pad_x = size_config["padding_x"]
        label_h = self._inside_label.height()

        # resting 位置：textarea 多行场景下应该停在文本第一行附近，
        # 而不是 wrapper 垂直中心（否则 textarea 越高 label 越居中越奇怪）。
        # 第一行文字的近似 y = wrapper 顶 + 当前 wrapper padding_top
        is_inside = self._label_placement == "inside"
        cur_pad_y = (
            size_config["inside_padding_y"]
            if is_inside and self._has_label()
            else size_config["padding_y"]
        )
        # 把 label 垂直居中在第一行高度内
        row_h = self._cached_row_height or self._calc_row_height()
        first_row_top = wrapper_y + cur_pad_y
        # 当 inside 模式下，文本本身被 inner_layout 推下 inside_input_top_space，
        # 所以 label resting 也应该跟着推下，否则和占位符不对齐
        if is_inside and self._has_label():
            first_row_top += size_config["inside_input_top_space"]
        y_rest = first_row_top + (row_h - label_h) // 2
        x_rest = wrapper_x + pad_x

        # floated 终点
        if self._label_placement == "outside":
            x_float = 0
            y_float = max(0, wrapper_y - label_h - 2)
        else:
            x_float = wrapper_x + pad_x + size_config.get("label_float_x", 0)
            y_float = wrapper_y + size_config.get("label_float_y", 6)

        x = int(x_rest + (x_float - x_rest) * progress)
        y = int(y_rest + (y_float - y_rest) * progress)
        self._inside_label.move(x, y)
        self._inside_label.raise_()

        c1 = self._label_color_resting
        c2 = self._label_color_floated
        r = int(c1.red() + (c2.red() - c1.red()) * progress)
        g = int(c1.green() + (c2.green() - c1.green()) * progress)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * progress)

        req_mark = ""
        if self._is_required and self._label_text:
            req_mark = f" <span style='color:{HEROUI_COLORS['danger'][500]};'>*</span>"
        self._inside_label.setTextFormat(Qt.TextFormat.RichText)
        self._inside_label.setText(
            f"<span style='color:rgb({r},{g},{b});'>{self._label_text}</span>{req_mark}"
        )
        self._inside_label.adjustSize()

    def _on_label_progress(self, progress: float):
        self._apply_label_progress(progress)
